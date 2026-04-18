"""
Phase 1 race-fix regression tests.

These tests lock in the invariant that Celery dispatches wait for the
enclosing transaction to commit (see Documents/REFACTOR_PLAN.md §Phase 1).
If anyone reverts a `transaction.on_commit(...)` wrap back to a plain
`.delay()`, the rollback test here fails.

The three behaviors under test:
    1. Happy path — signal registers an on_commit callback, task dispatches
       only after commit (not synchronously with the save).
    2. Rollback path — if the enclosing transaction rolls back, the task
       does NOT dispatch.
    3. Outside-transaction helper path — a helper called with no active
       transaction fires its dispatch immediately (on_commit is effectively
       a no-op).
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction as db_txn
from django.test import TransactionTestCase
from django.utils import timezone

from Tracker.models import CAPA, UserInvitation
from Tracker.tests.base import VectorTestCase

User = get_user_model()


class CeleryOnCommitDispatchTestCase(VectorTestCase):
    """Verify that wrapped dispatches are queued pre-commit and fire after."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='dispatch_user',
            email='dispatch@example.com',
            password='testpass',
        )

    @patch('Tracker.tasks.send_capa_assignment_notification.delay')
    def test_capa_assignment_dispatches_after_commit(self, mock_delay):
        """
        Signal handler notify_assignment wraps its dispatch in
        transaction.on_commit. During the captured block, .delay has not
        been invoked (it's queued as an on_commit callback). After the
        block exits (which emulates commit), the callback runs and .delay
        is called exactly once with the CAPA id.

        Django's captureOnCommitCallbacks populates the returned list in
        its finally clause (after the block exits), so len(callbacks)
        assertions belong outside the `with`.
        """
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            capa = CAPA.objects.create(
                capa_type='CORRECTIVE',
                severity='MINOR',
                problem_statement='race-fix happy-path check',
                initiated_by=self.user,
                assigned_to=self.user,
            )
            # Inside the block: on_commit callback is queued but .delay
            # has NOT been invoked. If someone reverts the wrap to a plain
            # .delay(), this assertion fails (delay fires synchronously).
            self.assertEqual(mock_delay.call_count, 0)

        # After block exits: captured callbacks execute, delay fires once.
        self.assertGreaterEqual(len(callbacks), 1)
        self.assertEqual(mock_delay.call_count, 1)
        mock_delay.assert_called_with(capa.id)


class CeleryRollbackDispatchTestCase(TransactionTestCase):
    """Verify that transaction rollback cancels pending Celery dispatches."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='rollback_user',
            email='rollback@example.com',
            password='testpass',
        )

    @patch('Tracker.tasks.send_capa_assignment_notification.delay')
    def test_rollback_cancels_capa_dispatch(self, mock_delay):
        """
        When the enclosing atomic() block rolls back, any on_commit
        callbacks registered within it are discarded. If the race-fix
        were reverted, mock_delay would have fired before the rollback
        and this assertion would fail.
        """
        try:
            with db_txn.atomic():
                CAPA.objects.create(
                    capa_type='CORRECTIVE',
                    severity='MINOR',
                    problem_statement='race-fix rollback check',
                    initiated_by=self.user,
                    assigned_to=self.user,
                )
                # Force rollback
                raise RuntimeError('simulated failure')
        except RuntimeError:
            pass

        # Task was NOT dispatched because the transaction rolled back.
        self.assertEqual(mock_delay.call_count, 0)

    @patch('Tracker.tasks.send_invitation_email_task.delay')
    def test_invitation_helper_fires_immediately_outside_transaction(self, mock_delay):
        """
        send_invitation_email(immediate=False) wraps its .delay in
        transaction.on_commit. Called outside any transaction (as in a
        management command or direct shell invocation), on_commit fires
        immediately — the task dispatch happens synchronously from the
        helper's perspective.
        """
        invitation = UserInvitation.objects.create(
            user=self.user,
            invited_by=self.user,
            token='test-token-race-fix',
            expires_at=timezone.now() + timedelta(days=1),
        )

        from Tracker.email_notifications import send_invitation_email
        # No outer atomic() wrapping — on_commit callback fires now.
        send_invitation_email(invitation.id, immediate=False)

        self.assertEqual(mock_delay.call_count, 1)
        mock_delay.assert_called_with(invitation.id)
