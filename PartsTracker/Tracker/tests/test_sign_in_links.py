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

    def test_the_sign_in_page_knows_whether_email_is_on(self):
        with override_settings(EMAIL_ENABLED=False):
            self.assertIs(self.client.get("/auth/sign-in-notice/").json()["email_enabled"], False)
        with override_settings(EMAIL_ENABLED=True):
            self.assertIs(self.client.get("/auth/sign-in-notice/").json()["email_enabled"], True)
