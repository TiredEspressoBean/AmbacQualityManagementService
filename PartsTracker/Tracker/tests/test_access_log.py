"""Access logging: one policy, and the failure path is the point.

NIST 800-171 3.3.4 asks to be told when audit logging fails. Before this,
three call sites disagreed -- one propagated, one warned, one used print() --
so the practice was unmet in two of three and a latent 500 in the third.

These tests pin the contract: never raise, always shout.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from auditlog.models import LogEntry

from Tracker.models import Tenant
from Tracker.services.core.access_log import record_access

User = get_user_model()


class RecordAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Access Log Co', slug='access-log-co')
        cls.user = User.objects.create_user(
            username='reader', email='reader@example.com', password='x', tenant=cls.tenant,
        )

    def test_writes_an_access_row(self):
        ok = record_access(
            obj=self.user, user=self.user, action_type='document_view',
            payload={'file_name': 'drawing.pdf'},
        )

        self.assertTrue(ok)
        entry = LogEntry.objects.filter(action=LogEntry.Action.ACCESS).latest('timestamp')
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.changes['action_type'], 'document_view')
        self.assertEqual(entry.changes['file_name'], 'drawing.pdf')

    def test_a_model_class_records_no_object_pk(self):
        """An AI query has no single subject, so `obj` may be a class.

        `getattr(SomeModel, 'pk')` returns a property descriptor rather than a
        value, so without the isinstance guard this wrote its repr into
        object_pk.
        """
        ok = record_access(
            obj=User, user=self.user, action_type='ai_query',
            object_repr='AI ai_query: User (3 results)',
            payload={'result_count': 3},
        )

        self.assertTrue(ok)
        entry = LogEntry.objects.filter(changes__action_type='ai_query').latest('timestamp')
        self.assertEqual(entry.object_pk, '')
        self.assertEqual(entry.object_repr, 'AI ai_query: User (3 results)')

    def test_a_failed_write_does_not_raise(self):
        """The request survives. This is the deliberate half of the policy."""
        with patch.object(LogEntry.objects, 'create', side_effect=RuntimeError('db gone')):
            ok = record_access(obj=self.user, user=self.user, action_type='document_view')

        self.assertFalse(ok)

    def test_a_failed_write_is_logged_at_error_with_a_stable_marker(self):
        """And this is the half that satisfies 3.3.4.

        Asserting on the marker rather than the message: alerting keys off
        `audit_write_failed`, so a reworded message must not silently stop
        paging anyone.
        """
        with patch.object(LogEntry.objects, 'create', side_effect=RuntimeError('db gone')):
            with self.assertLogs('compliance.access_control', level='ERROR') as captured:
                record_access(obj=self.user, user=self.user, action_type='document_view')

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertTrue(getattr(record, 'audit_write_failed', False))
        self.assertEqual(record.levelname, 'ERROR')
        # The traceback is what makes it diagnosable rather than just noisy.
        self.assertIsNotNone(record.exc_info)

    def test_a_failed_write_emits_no_access_granted(self):
        """A failure must not also look like a successful read.

        Both lines going out would make the compliance trail claim an access
        was recorded when it was not -- worse than the silence it replaced.
        """
        with patch.object(LogEntry.objects, 'create', side_effect=RuntimeError('db gone')):
            with self.assertLogs('compliance.access_control', level='INFO') as captured:
                record_access(obj=self.user, user=self.user, action_type='document_view')

        self.assertFalse(
            any(getattr(r, 'event_type', None) == 'ACCESS_GRANTED' for r in captured.records)
        )

    def test_a_successful_write_emits_the_compliance_line(self):
        with self.assertLogs('compliance.access_control', level='INFO') as captured:
            record_access(
                obj=self.user, user=self.user, action_type='document_download',
                payload={'classification': 'CONFIDENTIAL'}, remote_addr='10.0.0.9',
            )

        granted = [r for r in captured.records if getattr(r, 'event_type', None) == 'ACCESS_GRANTED']
        self.assertEqual(len(granted), 1)
        self.assertEqual(granted[0].action_type, 'document_download')
        self.assertEqual(granted[0].classification, 'CONFIDENTIAL')
        self.assertEqual(granted[0].remote_addr, '10.0.0.9')
