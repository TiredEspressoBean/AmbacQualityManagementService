"""Sign-in without email: invitation fixes and admin-issued reset links (user batch
2026-11-19). services/core/sign_in.py."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from Tracker.tests.base import TenantTestCase

User = get_user_model()


class _Fixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()  # the reset endpoints' throttle counts across tests otherwise
        from Tracker.models import TenantGroup, UserRole
        self.admin_group, _ = TenantGroup.objects.get_or_create(tenant=self.tenant_a, name="Tenant Admin")
        self.admin = User.objects.create_user(username="ta", email="ta@a.test", password="pw-admin-1",
                                              tenant=self.tenant_a)
        UserRole.objects.get_or_create(user=self.admin, group=self.admin_group)
        self.grant_tenant_permissions(self.admin, self.tenant_a, ['full_tenant_access', 'view_user',
                                                                  'add_user', 'change_user'])
        # A manager who may invite, but isn't a Tenant Admin.
        self.manager = User.objects.create_user(username="mgr", email="mgr@a.test", password="pw-mgr-1",
                                                tenant=self.tenant_a)
        self.grant_tenant_permissions(self.manager, self.tenant_a, ['full_tenant_access', 'view_user',
                                                                    'add_user', 'change_user'])
        # Someone set up (has signed in), and someone not yet.
        self.worker = User.objects.create_user(username="w", email="w@a.test", password="pw-worker-1",
                                               tenant=self.tenant_a)
        User.objects.filter(pk=self.worker.pk).update(last_login=timezone.now())
        self.worker.refresh_from_db()
        self.newbie = User.objects.create_user(username="n", email="n@a.test", password=None,
                                               tenant=self.tenant_a, is_active=False)
        self.authenticate_as(self.admin, self.tenant_a)

    def _invite(self, user):
        with patch("Tracker.email_notifications.send_invitation_email"):
            return self.client.post("/api/User/send-invitation/", {"user_id": user.id}, format="json")

    def _accept(self, token, password="a-New-pw-77"):
        self.client.force_authenticate(user=None)
        return self.client.post("/api/UserInvitations/accept/", {"token": token, "password": password},
                                format="json")


class InvitationFixTests(_Fixture):
    def test_accepting_one_link_kills_the_others(self):
        from Tracker.models import UserInvitation
        from Tracker.services.core.sign_in import create_invitation
        first = UserInvitation.objects.create(user=self.newbie, invited_by=self.admin, token="t-first",
                                              expires_at=timezone.now() + timedelta(days=7))
        second = UserInvitation.objects.create(user=self.newbie, invited_by=self.admin, token="t-second",
                                               expires_at=timezone.now() + timedelta(days=7))
        self.assertEqual(self._accept("t-first").status_code, 200)
        second.refresh_from_db()
        self.assertFalse(second.is_valid())
        r = self._accept("t-second", password="Another-pw-88")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIsNotNone(create_invitation)  # imported for its rule, used below

    def test_resend_kills_the_old_link(self):
        from Tracker.models import UserInvitation
        old = UserInvitation.objects.get(pk=self._invite(self.newbie).json()["invitation_id"])
        with patch("Tracker.email_notifications.send_invitation_email"):
            r = self.client.post("/api/UserInvitations/resend/", {"invitation_id": old.id}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("/signup?token=", r.json()["invitation_url"])
        old.refresh_from_db()
        self.assertFalse(old.is_valid())

    def test_an_account_already_set_up_takes_no_invitation(self):
        from Tracker.models import UserInvitation
        stale = UserInvitation.objects.create(user=self.worker, invited_by=self.admin, token="t-stale",
                                              expires_at=timezone.now() + timedelta(days=7))
        r = self._accept("t-stale")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["detail"],
                         "This account is already set up — sign in, or ask your administrator for a reset link.")
        self.worker.refresh_from_db()
        self.assertTrue(self.worker.check_password("pw-worker-1"))
        self.authenticate_as(self.admin, self.tenant_a)
        r = self._invite(self.worker)
        self.assertEqual((r.status_code, r.json()["code"]), (400, "already_set_up"))

    def test_an_invitation_works_for_the_days_it_was_sent_for(self):
        with patch("Tracker.email_notifications.send_invitation_email"):
            r = self.client.post("/api/User/send-invitation/", {"user_id": self.newbie.id, "valid_days": 2},
                                 format="json")
        token = r.json()["invitation_url"].split("token=")[1]
        with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(days=3)):
            r = self._accept(token)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["detail"], "This invitation has expired")

    def test_the_bulk_path_gets_the_default_lifetime(self):
        from Tracker.models import UserInvitation
        from Tracker.services.core.user_reconcile import invite_uninvited
        User.objects.filter(pk=self.newbie.pk).update(is_active=True)  # loaded, not yet invited
        with patch("Tracker.email_notifications.send_invitation_email"):
            invite_uninvited(self.tenant_a, acting_user=self.admin)
        inv = UserInvitation.objects.filter(user=self.newbie).first()
        self.assertIsNotNone(inv)
        self.assertAlmostEqual((inv.expires_at - timezone.now()).days, 6, delta=1)

    def test_resend_by_person_is_a_new_link_for_the_days_chosen(self):
        old_url = self._invite(self.newbie).json()["invitation_url"]
        with patch("Tracker.email_notifications.send_invitation_email"):
            r = self.client.post("/api/UserInvitations/resend/",
                                 {"user_id": self.newbie.id, "valid_days": 3}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertNotEqual(r.json()["invitation_url"], old_url)
        expires = timezone.datetime.fromisoformat(r.json()["expires_at"].replace("Z", "+00:00"))
        self.assertAlmostEqual((expires - timezone.now()).total_seconds() / 86400, 3, delta=0.01)
        self.assertEqual(self._accept(old_url.split("token=")[1]).status_code, 400)
        self.assertEqual(self._accept(r.json()["invitation_url"].split("token=")[1]).status_code, 200)

    def _validate(self, token):
        self.client.force_authenticate(user=None)
        return self.client.post("/api/UserInvitations/validate-token/", {"token": token}, format="json").json()

    def test_a_replaced_link_says_so_when_it_opens_and_when_used(self):
        replaced = "This invitation link was replaced by a newer one. Ask for the latest link."
        old = self._invite(self.newbie).json()["invitation_url"].split("token=")[1]
        self.assertEqual((self._validate(old)["valid"], self._validate(old)["detail"]), (True, None))
        self.authenticate_as(self.admin, self.tenant_a)
        with patch("Tracker.email_notifications.send_invitation_email"):
            self.client.post("/api/UserInvitations/resend/", {"user_id": self.newbie.id}, format="json")
        self.assertEqual((self._validate(old)["valid"], self._validate(old)["detail"]), (False, replaced))
        self.assertEqual(self._accept(old).json()["detail"], replaced)

    def test_an_accepted_link_says_where_to_go_and_a_mangled_one_says_check_it(self):
        token = self._invite(self.newbie).json()["invitation_url"].split("token=")[1]
        self.assertEqual(self._accept(token).status_code, 200)
        set_up = "This account is already set up — sign in, or ask your administrator for a reset link."
        self.assertEqual(self._validate(token)["detail"], set_up)
        self.assertEqual(self._accept(token, password="Again-pw-99").json()["detail"], set_up)
        invalid = "This invitation link isn't valid — check you have the whole link, or ask for a new one."
        self.assertEqual(self._validate(token[:-4])["detail"], invalid)
        self.assertEqual(self._accept(token[:-4]).json()["detail"], invalid)

    def test_an_expired_link_reads_expired_and_a_set_up_account_reads_set_up(self):
        from Tracker.models import UserInvitation
        UserInvitation.objects.create(user=self.newbie, invited_by=self.admin, token="t-old",
                                      expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self._validate("t-old")["detail"], "This invitation has expired")
        UserInvitation.objects.create(user=self.worker, invited_by=self.admin, token="t-worker",
                                      expires_at=timezone.now() + timedelta(days=7))
        self.assertEqual(self._validate("t-worker")["detail"],
                         "This account is already set up — sign in, or ask your administrator for a reset link.")

    def test_with_email_off_an_invitation_is_a_link_and_nothing_is_sent(self):
        with override_settings(EMAIL_ENABLED=False), \
                patch("Tracker.email_notifications.send_invitation_email") as send:
            r = self.client.post("/api/User/send-invitation/", {"user_id": self.newbie.id}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.json()["email_sent"], False)
        self.assertIn("/signup?token=", r.json()["invitation_url"])
        send.assert_not_called()

    def test_set_up_is_a_usable_password_not_a_sign_in(self):
        # Loaded with a password, never signed in (the seeded staff): set up.
        loaded = User.objects.create_user(username="ld", email="ld@a.test", password="pw-loaded-1",
                                          tenant=self.tenant_a)
        self.assertIsNone(loaded.last_login)
        r = self._invite(loaded)
        self.assertEqual((r.status_code, r.json()["code"]), (400, "already_set_up"))
        self.assertEqual(self.client.post(f"/api/User/{loaded.id}/reset-link/").status_code, 200)
        rows = {u["id"]: u for u in self.client.get("/api/User/?limit=200").json()["results"]}
        self.assertIs(rows[loaded.id]["is_set_up"], True)
        self.assertIs(rows[self.newbie.id]["is_set_up"], False)

    def test_only_someone_who_may_invite_sees_or_resends_links(self):
        from Tracker.models import UserInvitation
        self._invite(self.newbie)
        clerk = User.objects.create_user(username="c", email="c@a.test", password="pw-c-1", tenant=self.tenant_a)
        self.grant_tenant_permissions(clerk, self.tenant_a, ['full_tenant_access', 'view_userinvitation'])
        self.authenticate_as(clerk, self.tenant_a)
        rows = self.client.get("/api/UserInvitations/").json()["results"]
        self.assertTrue(rows)
        self.assertTrue(all(row["invitation_url"] is None for row in rows))
        inv = UserInvitation.objects.filter(user=self.newbie).first()
        r = self.client.post("/api/UserInvitations/resend/", {"invitation_id": inv.id}, format="json")
        self.assertEqual(r.status_code, 403, r.content)


class ResetLinkTests(_Fixture):
    def _link(self, user):
        return self.client.post(f"/api/User/{user.id}/reset-link/")

    def _confirm(self, url, password):
        uid, token = url.rstrip("/").split("/")[-2:]
        self.client.force_authenticate(user=None)
        # The path the Reset password page posts to.
        return self.client.post("/auth/password/reset/confirm/",
                                {"uid": uid, "token": token, "new_password1": password,
                                 "new_password2": password}, format="json")

    def test_a_reset_link_works_once_and_signs_out_elsewhere(self):
        from rest_framework.authtoken.models import Token
        Token.objects.create(user=self.worker)
        r = self._link(self.worker)
        self.assertEqual(r.status_code, 200, r.content)
        url = r.json()["reset_url"]
        self.assertIn("/reset-password/", url)
        r = self._confirm(url, "Fresh-pw-2026!")
        self.assertEqual(r.status_code, 200, r.content)
        self.worker.refresh_from_db()
        self.assertTrue(self.worker.check_password("Fresh-pw-2026!"))
        self.assertFalse(Token.objects.filter(user=self.worker).exists())
        # Spent: the token hashed the old password.
        self.assertEqual(self._confirm(url, "Again-pw-2026!").status_code, 400)

    def test_who_may_have_one(self):
        self.assertEqual(self._link(self.admin).status_code, 400)          # not for yourself
        r = self._link(self.newbie)                                           # never set up
        self.assertEqual(r.json()["detail"], "Not set up yet — send an invitation instead.")
        self.authenticate_as(self.manager, self.tenant_a)
        r = self._link(self.admin)                                            # a lesser manager, an admin
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Only a Tenant Admin", r.json()["detail"])
        self.assertEqual(self._link(self.worker).status_code, 200)           # a manager, a worker
        self.authenticate_as(self.worker, self.tenant_a)                      # can't invite
        self.assertEqual(self._link(self.manager).status_code, 403)

    def _later(self, **delta):
        """Clocks moved on: the app's and the token generator's."""
        from contextlib import ExitStack
        later = timezone.now() + timedelta(**delta)
        stack = ExitStack()
        stack.enter_context(patch("django.utils.timezone.now", return_value=later))
        stack.enter_context(patch("django.contrib.auth.tokens.PasswordResetTokenGenerator._now",
                                  return_value=later.replace(tzinfo=None)))
        return stack

    def test_a_link_works_for_the_days_it_was_issued_for(self):
        url = self.client.post(f"/api/User/{self.worker.id}/reset-link/", {"valid_days": 1},
                               format="json").json()["reset_url"]
        with self._later(days=2):  # the token is still inside its 30-day ceiling
            r = self._confirm(url, "Late-pw-2026!")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["detail"], "This reset link has expired. Ask for a new one.")
        self.authenticate_as(self.admin, self.tenant_a)
        url = self.client.post(f"/api/User/{self.worker.id}/reset-link/", {"valid_days": 7},
                               format="json").json()["reset_url"]
        with self._later(days=6):
            self.assertEqual(self._confirm(url, "Day-six-pw-26!").status_code, 200)

    def test_valid_for_is_one_to_thirty_days_and_seven_by_default(self):
        r = self._link(self.worker)
        expires = timezone.datetime.fromisoformat(r.json()["expires_at"].replace("Z", "+00:00"))
        self.assertAlmostEqual((expires - timezone.now()).days, 6, delta=1)
        r = self.client.post(f"/api/User/{self.worker.id}/reset-link/", {"valid_days": 31}, format="json")
        self.assertEqual(r.status_code, 400, r.content)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_the_email_path_still_resets_and_signs_out(self):
        from django.core import mail
        from rest_framework.authtoken.models import Token
        Token.objects.create(user=self.worker)
        self.client.force_authenticate(user=None)
        r = self.client.post("/auth/password/reset/", {"email": self.worker.email}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = mail.outbox[-1].body
        url = next(w for w in body.split() if "/reset-password/" in w)
        # An emailed link works for a day.
        with patch("django.contrib.auth.tokens.PasswordResetTokenGenerator._now",
                   return_value=(timezone.now() + timedelta(hours=25)).replace(tzinfo=None)):
            self.assertEqual(self._confirm(url, "Mailed-late-26!").status_code, 400)
        self.assertEqual(self._confirm(url, "Mailed-pw-2026!").status_code, 200)
        self.assertFalse(Token.objects.filter(user=self.worker).exists())

    def _check(self, url):
        uid, token = url.rstrip("/").split("/")[-2:]
        self.client.force_authenticate(user=None)
        return self.client.post("/auth/password/reset/check/", {"uid": uid, "token": token},
                                format="json").json()

    def test_the_page_knows_a_link_is_spent_or_expired_when_it_opens(self):
        url = self._link(self.worker).json()["reset_url"]
        self.assertEqual(self._check(url), {"valid": True, "detail": None})
        self.assertEqual(self._confirm(url, "Fresh-pw-2026!").status_code, 200)
        self.assertEqual(self._check(url)["detail"], "This reset link has already been used. Ask for a new one.")
        self.authenticate_as(self.admin, self.tenant_a)
        url = self.client.post(f"/api/User/{self.worker.id}/reset-link/", {"valid_days": 1},
                               format="json").json()["reset_url"]
        with self._later(days=2):
            self.assertEqual(self._check(url)["detail"], "This reset link has expired. Ask for a new one.")
        uid = url.rstrip("/").split("/")[-2]
        self.assertFalse(self._check(f"/reset-password/{uid}/garbage-token/")["valid"])

    def test_email_is_opt_in(self):
        from PartsTrackerApp.settings import email_config
        smtp = "django.core.mail.backends.smtp.EmailBackend"
        dummy = "django.core.mail.backends.dummy.EmailBackend"
        self.assertEqual(email_config({}), (False, dummy))
        self.assertEqual(email_config({"EMAIL_HOST": "smtp.sendgrid.net", "EMAIL_BACKEND": smtp}),
                         (False, dummy))  # a host configured doesn't turn it on
        self.assertEqual(email_config({"EMAIL_ENABLED": "true", "EMAIL_HOST": "smtp.sendgrid.net"}),
                         (True, smtp))
        console = "django.core.mail.backends.console.EmailBackend"
        self.assertEqual(email_config({"EMAIL_BACKEND": console}), (False, console))  # dev's choice kept

    def test_with_email_off_a_notification_is_suppressed_not_sent(self):
        from Tracker.models import NotificationOutbox, NotificationStatus
        from Tracker.services.core.notifications.tasks import dispatch_outbox_row
        row = NotificationOutbox.objects.create(tenant=self.tenant_a, event_code="test", channel="email",
                                                user=self.worker, rendered_subject="s",
                                                rendered_body_text="b", idempotency_key="email-off-1")
        with override_settings(EMAIL_ENABLED=False):
            result = dispatch_outbox_row.apply(args=[row.id]).get()
        row.refresh_from_db()
        self.assertEqual((result["status"], row.status), ("suppressed", NotificationStatus.SUPPRESSED))

    def test_the_sign_in_page_knows_whether_email_is_on(self):
        with override_settings(EMAIL_ENABLED=False):
            self.assertIs(self.client.get("/auth/sign-in-notice/").json()["email_enabled"], False)
        with override_settings(EMAIL_ENABLED=True):
            self.assertIs(self.client.get("/auth/sign-in-notice/").json()["email_enabled"], True)
