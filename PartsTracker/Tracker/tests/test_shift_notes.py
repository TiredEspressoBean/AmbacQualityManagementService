"""Shift-notes tests — service behavior (audience, effective window, edit-lock,
retract, ack) and API permission gating (leads author, operators read + ack)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from Tracker.models import ShiftNoteAck
from Tracker.services.mes.shift_notes import (
    acknowledge_shift_note,
    active_shift_notes_for_user,
    edit_shift_note,
    publish_shift_note,
    retract_shift_note,
)
from Tracker.tests.base import TenantTestCase

User = get_user_model()


class ShiftNoteServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.lead = self.user_a
        self.operator = User.objects.create_user(
            username="op_svc", email="op_svc@tenant-a.com",
            password="x", tenant=self.tenant_a,
        )
        self.op_group = self.grant_tenant_permissions(
            self.operator, self.tenant_a,
            ["view_shiftnote", "view_shiftnoteack", "full_tenant_access"],
        )

    def test_publish_creates_note(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="Prioritize WO-1")
        self.assertFalse(note.is_voided)
        self.assertEqual(note.author, self.lead)

    def test_publish_rejects_empty_body(self):
        with self.assertRaises(ValueError):
            publish_shift_note(author=self.lead, tenant=self.tenant_a, body="   ")

    def test_empty_audience_is_visible_to_all(self):
        publish_shift_note(author=self.lead, tenant=self.tenant_a, body="everyone")
        self.assertEqual(len(active_shift_notes_for_user(self.operator, tenant=self.tenant_a)), 1)

    def test_audience_role_match(self):
        publish_shift_note(author=self.lead, tenant=self.tenant_a, body="ops only",
                           audience_roles=[self.op_group.name])
        publish_shift_note(author=self.lead, tenant=self.tenant_a, body="others only",
                           audience_roles=["SomeOtherGroup"])
        bodies = {n.body for n in active_shift_notes_for_user(self.operator, tenant=self.tenant_a)}
        self.assertIn("ops only", bodies)
        self.assertNotIn("others only", bodies)

    def test_active_excludes_acknowledged(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="ack me")
        acknowledge_shift_note(note, user=self.operator)
        self.assertEqual(active_shift_notes_for_user(self.operator, tenant=self.tenant_a), [])

    def test_active_respects_effective_window(self):
        publish_shift_note(author=self.lead, tenant=self.tenant_a, body="later",
                           effective_from=timezone.now() + timedelta(hours=1))
        publish_shift_note(author=self.lead, tenant=self.tenant_a, body="expired",
                           effective_until=timezone.now() - timedelta(hours=2))
        bodies = {n.body for n in active_shift_notes_for_user(self.operator, tenant=self.tenant_a)}
        self.assertNotIn("later", bodies)
        self.assertNotIn("expired", bodies)

    def test_edit_allowed_before_ack_locked_after(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="v1")
        edit_shift_note(note, body="v2")
        self.assertEqual(note.body, "v2")
        acknowledge_shift_note(note, user=self.operator)
        self.assertTrue(note.is_locked)
        with self.assertRaises(ValueError):
            edit_shift_note(note, body="v3")

    def test_acknowledge_is_idempotent(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="x")
        acknowledge_shift_note(note, user=self.operator)
        acknowledge_shift_note(note, user=self.operator)
        self.assertEqual(ShiftNoteAck.objects.filter(note=note, user=self.operator).count(), 1)

    def test_retract_voids_and_drops_from_active(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="oops")
        retract_shift_note(note, user=self.lead, reason="mistake")
        note.refresh_from_db()
        self.assertTrue(note.is_voided)
        self.assertEqual(active_shift_notes_for_user(self.operator, tenant=self.tenant_a), [])


class ShiftNoteApiTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.lead = self.user_a
        self.grant_tenant_permissions(
            self.lead, self.tenant_a,
            ["add_shiftnote", "change_shiftnote", "view_shiftnote",
             "view_shiftnoteack", "full_tenant_access"],
        )
        self.operator = User.objects.create_user(
            username="op_api", email="op_api@tenant-a.com",
            password="x", tenant=self.tenant_a,
        )
        self.grant_tenant_permissions(
            self.operator, self.tenant_a,
            ["view_shiftnote", "view_shiftnoteack", "full_tenant_access"],
        )

    def test_lead_can_create(self):
        self.authenticate_as(self.lead, self.tenant_a)
        resp = self.client.post("/api/ShiftNotes/", {"body": "hi", "audience_roles": []}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_operator_cannot_create(self):
        self.authenticate_as(self.operator, self.tenant_a)
        resp = self.client.post("/api/ShiftNotes/", {"body": "hi", "audience_roles": []}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_ack_required_note_exposes_roster(self):
        self.authenticate_as(self.lead, self.tenant_a)
        resp = self.client.post(
            "/api/ShiftNotes/",
            {"body": "Gauge #7 out of cal - do not use.", "audience_roles": [],
             "acknowledgment_required": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(resp.data["acknowledgment_required"])
        self.assertEqual(resp.data["ack_count"], 0)
        self.assertEqual(resp.data["acknowledged_by"], [])
        note_id = resp.data["id"]

        # Operator acknowledges.
        self.authenticate_as(self.operator, self.tenant_a)
        self.assertEqual(
            self.client.post(f"/api/ShiftNotes/{note_id}/acknowledge/").status_code, 200
        )

        # Lead sees the roster: one acker, audience sized.
        self.authenticate_as(self.lead, self.tenant_a)
        got = self.client.get(f"/api/ShiftNotes/{note_id}/")
        self.assertEqual(got.data["ack_count"], 1)
        self.assertEqual(len(got.data["acknowledged_by"]), 1)
        self.assertGreaterEqual(got.data["audience_size"], 1)

    def test_api_create_routes_through_publish_and_emits(self):
        # Guards the fix: perform_create must go through publish_shift_note so
        # the feed alert (shift_note.published) fires — plain serializer.save()
        # would persist the row but skip the notification.
        from unittest.mock import patch

        self.authenticate_as(self.lead, self.tenant_a)
        with patch("Tracker.services.core.notifications.emit") as mock_emit:
            resp = self.client.post(
                "/api/ShiftNotes/",
                {"body": "Run WO-51 next.", "audience_roles": []},
                format="json",
            )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(mock_emit.called)
        self.assertEqual(mock_emit.call_args.args[0], "shift_note.published")

    def test_operator_can_read_active_and_acknowledge(self):
        note = publish_shift_note(author=self.lead, tenant=self.tenant_a, body="see me")
        self.authenticate_as(self.operator, self.tenant_a)

        active = self.client.get("/api/ShiftNotes/active/")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.data["count"], 1)

        ack = self.client.post(f"/api/ShiftNotes/{note.id}/acknowledge/")
        self.assertEqual(ack.status_code, 200)

        after = self.client.get("/api/ShiftNotes/active/")
        self.assertEqual(after.data["count"], 0)
