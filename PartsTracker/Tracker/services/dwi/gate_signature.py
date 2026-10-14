"""Signing an individual block inside a substep, and undoing it before submission.

A substep's body can carry attestation blocks, and each one chooses its own
assurance (`AttestationCheckpoint.attrs.kind`):

- ``confirm`` — the operator ticks it. Recorded under their login, nothing more.
- ``signature`` — the operator draws and re-enters their own password. The block
  is the unit: its label is the meaning, so the record says what was signed for
  rather than naming the whole substep.

Each signature is a `SubstepGateCompletion`, keyed to (execution, substep, node).
That row already carried every field this needs — signer, server time,
verification method, meaning, IP — and nothing wrote one.

**Provisional until the substep is submitted.** A signature made while the work is
still in hand is not yet a claim about finished work, so it can be undone: by the
signer, always; by a supervisor holding `clear_gate_signature`, for the case where
someone signs and goes off shift. Once a live `SubstepCompletion` exists the
substep has been submitted, undo is refused, and only `void_substepcompletion`
retracts it — with a reason, and re-opening the substep for a fresh signature.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils import timezone


SIGNATURE_KIND = "signature"


def attestation_nodes(substep) -> dict[str, dict]:
    """{node_id: attrs} for the attestation blocks in a substep's body."""
    found: dict[str, dict] = {}

    def walk(node):
        if isinstance(node, dict):
            attrs = node.get("attrs") or {}
            if node.get("type") == "attestationCheckpoint" and attrs.get("node_id"):
                found[str(attrs["node_id"])] = attrs
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(substep.body_blocks)
    return found


def signature_node_ids(substep) -> list[str]:
    """The blocks in this substep that ask for a signature and a password."""
    return [nid for nid, attrs in attestation_nodes(substep).items()
            if attrs.get("kind") == SIGNATURE_KIND]


def _live_completion(substep, step_execution=None, batch_execution=None):
    from Tracker.models import SubstepCompletion
    return (SubstepCompletion.objects  # tenant-safe: keyed to a tenant-scoped execution
            .filter(step_execution=step_execution, batch_execution=batch_execution,
                    substep=substep, is_voided=False, deleted_at__isnull=True)
            .first())


def signed_node_ids(substep, step_execution=None, batch_execution=None) -> set[str]:
    """Which of this substep's blocks already carry a live signature."""
    from Tracker.models import SubstepGateCompletion
    return set(SubstepGateCompletion.objects  # tenant-safe: keyed to a scoped execution
               .filter(substep=substep, step_execution=step_execution,
                       batch_execution=batch_execution, deleted_at__isnull=True)
               .values_list('node_id', flat=True))


def unsigned_signature_blocks(substep, step_execution=None, batch_execution=None) -> list[str]:
    """Labels of the signature blocks still waiting to be signed."""
    nodes = attestation_nodes(substep)
    signed = signed_node_ids(substep, step_execution, batch_execution)
    return [(nodes[nid].get("label") or substep.title)
            for nid in signature_node_ids(substep) if nid not in signed]


def sign_gate(*, substep, node_id, user, signature_data, password,
              step_execution=None, batch_execution=None, ip_address=None):
    """Record one block's signature. Returns the SubstepGateCompletion.

    Raises:
        ValidationError: the node isn't a signature block on this substep, the
            substep is already submitted, the block is already signed, or the
            drawing or password is missing or wrong.
    """
    from Tracker.models import SubstepGateCompletion
    from Tracker.services.core.second_person import verify_own_password

    attrs = attestation_nodes(substep).get(str(node_id))
    if attrs is None or attrs.get("kind") != SIGNATURE_KIND:
        raise ValidationError("That block doesn't ask for a signature.")
    if _live_completion(substep, step_execution, batch_execution) is not None:
        raise ValidationError(
            f"'{substep.title}' has already been submitted; its signatures are part of "
            "the record now. A QA void re-opens it.")
    if SubstepGateCompletion.objects.filter(  # tenant-safe: keyed to a scoped execution
            step_execution=step_execution, batch_execution=batch_execution,
            substep=substep, node_id=str(node_id), deleted_at__isnull=True).exists():
        raise ValidationError("That block is already signed. Undo it first to sign again.")
    if not signature_data:
        raise ValidationError("Draw your signature, then confirm with your password.")
    refusal = verify_own_password(tenant=substep.tenant, user=user, password=password or "")
    if refusal:
        raise ValidationError(refusal)

    return SubstepGateCompletion.objects.create(
        tenant=substep.tenant,
        step_execution=step_execution,
        batch_execution=batch_execution,
        substep=substep,
        node_id=str(node_id),
        completed_by=user,
        signature_data=signature_data,
        # The block's own label, so the record says what was signed for. Falls
        # back to the substep only when the block is unlabelled.
        signature_meaning=(attrs.get("label") or substep.title),
        verified_at=timezone.now(),
        verification_method="PASSWORD",
        ip_address=ip_address,
    )


def clear_gate_signature(gate, user, *, email: str = "", password: str = "") -> None:
    """Undo a provisional signature. Soft-deleted, so the block can be signed again
    (the uniqueness constraint ignores deleted rows) and the attempt stays in history.

    Someone else's signature needs that person's authority, not the operator's: a
    shop terminal has one session, so a supervisor clearing a block cannot be "the
    logged-in user with a permission". They identify themselves the way every other
    second-person act here does — their own email and password at the keyboard,
    checked against `clear_gate_signature` and throttled.

    Raises:
        ValidationError: the substep has been submitted, or this is someone else's
            signature and no authorised second person stood behind it.
    """
    if gate.deleted_at is not None:
        raise ValidationError("That signature has already been cleared.")
    if _live_completion(gate.substep, gate.step_execution, gate.batch_execution) is not None:
        raise ValidationError(
            f"'{gate.substep.title}' has been submitted, so its signatures stand. "
            "Ask QA to void the completion if it's wrong.")
    if gate.completed_by_id != user.pk:
        from Tracker.services.core.second_person import verify_second_person

        if not (email or password):
            raise ValidationError(
                f"That's {gate.completed_by.get_username()}'s signature. A supervisor can "
                "clear it if they've gone off shift — they sign in here to do it.")
        _, failure = verify_second_person(
            tenant=gate.tenant, actor=user, email=email, password=password,
            permission='clear_gate_signature',
            throttle_prefix='gate_signature_clear', code_prefix='clear_signature',
            messages={'not_permitted': "That user can't clear someone else's signature."},
        )
        if failure:
            raise ValidationError(failure[0])
    gate.deleted_at = timezone.now()
    gate.archived = True
    gate.save(update_fields=['deleted_at', 'archived', 'updated_at'])
