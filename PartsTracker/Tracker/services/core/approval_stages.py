"""Sequential approvals as ordered stages (user decision 2026-10-29).

A SEQUENTIAL request runs in stages. Each stage is the request's user assignments
and group assignments that share a `sequence_order`; an assignment with no order (a
legacy group, or a role user added without one) belongs to a final stage after the
numbered ones. The stages come from the template's `approval_stages` when the request
is made (`assign_from_template`), so a template edit never re-orders a request in
flight.

- **A stage is done** when every user assigned to it has approved, and each group in
  it has a member who claimed it (a user assignment at the same order, source CLAIMED)
  — that member's approval is then part of "every user". A member named in the same
  stage covers the group too. A group stage is required.
- **Only the open stage acts.** The open stage is the first one not done. Approve and
  reject are refused for anyone outside it ("Not your turn — waiting on …"), as
  21 CFR 11.10(f) expects out-of-sequence steps to be blocked. A group member
  answering the open stage claims it in the same act.
- **One person, one stage.** A response is per person per request already; a member
  of a group is also refused the group if they're named in another stage.
- **Reject** at any stage ends the request (check_approval_status). **Withdraw** is
  refused once a later stage has answered.
- Only the open stage is notified, and the next one when it opens.

PARALLEL requests don't come through here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Orderless assignments sort after every numbered stage.
FINAL = 10 ** 6


@dataclass
class Stage:
    order: int
    user_ids: list = field(default_factory=list)       # required user assignments at this order
    claimed_ids: list = field(default_factory=list)    # of those, the ones claimed from a group
    group_ids: list = field(default_factory=list)


def _order(value) -> int:
    return FINAL if value is None else value


def stages(request) -> list[Stage]:
    """The request's stages, in order."""
    from Tracker.models import ApproverAssignmentSource
    by_order: dict[int, Stage] = {}
    for a in request.approver_assignments.filter(is_required=True):
        st = by_order.setdefault(_order(a.sequence_order), Stage(_order(a.sequence_order)))
        st.user_ids.append(a.user_id)
        if a.assignment_source == ApproverAssignmentSource.CLAIMED:
            st.claimed_ids.append(a.user_id)
    for g in request.group_assignments.all():
        st = by_order.setdefault(_order(g.sequence_order), Stage(_order(g.sequence_order)))
        st.group_ids.append(g.group_id)
    return [by_order[k] for k in sorted(by_order)]


def _approved_ids(request) -> set:
    from Tracker.models import ApprovalDecision
    return set(request.responses.filter(decision=ApprovalDecision.APPROVED)
               .values_list('approver_id', flat=True))


def _members(group_ids) -> dict:
    """{group_id: set(user ids)}"""
    from Tracker.models import UserRole
    out: dict = {g: set() for g in group_ids}
    for gid, uid in UserRole.objects.filter(group_id__in=list(group_ids)).values_list('group_id', 'user_id'):
        out.setdefault(gid, set()).add(uid)
    return out


def _unclaimed_groups(stage: Stage, members: dict) -> list:
    """Groups in the stage that no member covers yet. A member assigned to the same
    stage — named, or claimed from the group — covers it: they must approve for the
    stage to be done anyway, and a second member would only be asked to sign the same
    stage twice over."""
    present = set(stage.user_ids)
    return [g for g in stage.group_ids if not (members.get(g, set()) & present)]


def open_stage(request) -> Stage | None:
    """The first stage not yet done; None when every stage is."""
    approved = _approved_ids(request)
    all_stages = stages(request)
    members = _members({g for st in all_stages for g in st.group_ids})
    for st in all_stages:
        if any(u not in approved for u in st.user_ids) or _unclaimed_groups(st, members):
            return st
    return None


def _named_elsewhere(request, user_id, order) -> bool:
    return request.approver_assignments.filter(user_id=user_id).exclude(
        sequence_order=None if order == FINAL else order).exists()


def turn(request, user):
    """(may_act, group_to_claim, refusal) for `user` on `request`'s open stage.

    `group_to_claim` is the group a member's answer will claim (None when they're named
    in the stage). `refusal` is the message when they may not act.
    """
    st = open_stage(request)
    if st is None:
        return False, None, "Every stage of this approval is done."
    if user.id in st.user_ids:
        return True, None, None
    members = _members(st.group_ids)
    for gid in _unclaimed_groups(st, members):
        if user.id in members.get(gid, set()) and not _named_elsewhere(request, user.id, st.order):
            return True, gid, None
    return False, None, f"Not your turn — waiting on {waiting_on(request, st)}."


def waiting_on(request, st: Stage) -> str:
    """Who the open stage is waiting on, in words."""
    from Tracker.models import TenantGroup, User
    approved = _approved_ids(request)
    names = [u.get_full_name() or u.get_username()
             for u in User.objects.filter(id__in=[u for u in st.user_ids if u not in approved])]
    members = _members(st.group_ids)
    groups = TenantGroup.objects.filter(id__in=_unclaimed_groups(st, members))  # tenant-safe: the request's groups
    names += [g.name for g in groups]
    return ", ".join(names) or "the current stage"


def pending_users(request) -> list:
    """Who the open stage waits on: its named users who haven't approved, and the
    members of its unclaimed groups who aren't named in another stage."""
    from Tracker.models import User
    st = open_stage(request)
    if st is None:
        return []
    approved = _approved_ids(request)
    ids = {u for u in st.user_ids if u not in approved}
    members = _members(st.group_ids)
    for gid in _unclaimed_groups(st, members):
        ids |= {u for u in members.get(gid, set()) if not _named_elsewhere(request, u, st.order)}
    return list(User.objects.filter(id__in=ids, is_active=True))


def claim_for_turn(request, user, group_id):
    """Turn a group member's answer into a claim on the open stage: a required user
    assignment at that stage's order."""
    from Tracker.models import ApproverAssignment, ApproverAssignmentSource
    st = open_stage(request)
    ApproverAssignment.objects.get_or_create(
        approval_request=request, user=user,
        defaults=dict(is_required=True, sequence_order=None if st.order == FINAL else st.order,
                      assignment_source=ApproverAssignmentSource.CLAIMED, assigned_by=user))


def withdraw_refusal(request, approver_id) -> str | None:
    """A response stands once a later stage has answered."""
    from Tracker.models import ApprovalDecision
    mine = request.approver_assignments.filter(user_id=approver_id).first()
    if mine is None:
        return None
    k = _order(mine.sequence_order)
    later = [a.user_id for a in request.approver_assignments.all() if _order(a.sequence_order) > k]
    if request.responses.filter(approver_id__in=later).exclude(
            decision=ApprovalDecision.WITHDRAWN).exists():
        return "A later stage has already answered, so this response stands."
    return None


def assign_from_template(request, template, tenant) -> None:
    """Lay a SEQUENTIAL request's stages out from the template.

    `approval_stages` gives the order. A template without stages keeps the old shape:
    its default approvers in order, its groups after them. The template's auto-assign
    role becomes one final stage — every member required under ALL_REQUIRED, any one
    member (the role's group) otherwise. A template without stages puts the role in its
    groups' final stage instead.
    """
    from Tracker.models import (
        ApprovalFlows, ApproverAssignment, ApproverAssignmentSource, GroupApproverAssignment,
        TenantGroup, User,
    )
    raw = [s for s in (template.approval_stages or []) if (s.get('users') or s.get('groups'))]
    legacy = not raw
    if legacy:
        raw = [{'users': [u.id]} for u in template.default_approvers.all()]
        group_ids = list(template.default_groups.values_list('id', flat=True))
        if group_ids:
            raw.append({'groups': group_ids})

    for i, stage in enumerate(raw):
        for uid in stage.get('users') or []:
            ApproverAssignment.objects.get_or_create(
                approval_request=request, user_id=uid,
                defaults=dict(is_required=True, sequence_order=i,
                              assignment_source=ApproverAssignmentSource.TEMPLATE_DEFAULT))
        for gid in stage.get('groups') or []:
            GroupApproverAssignment.objects.create(
                approval_request=request, group_id=gid, sequence_order=i,
                assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP)

    if template.auto_assign_by_role:
        # A template without stages keeps its role in the same final stage as its groups
        # — its role is usually one of them (a PCR's QA Manager), and a later stage of
        # the same people would bar them from the group stage before it.
        final = len(raw) - 1 if (legacy and raw and raw[-1].get('groups')) else len(raw)
        group = TenantGroup.objects.filter(tenant=tenant, name=template.auto_assign_by_role).first()  # tenant-safe
        if template.approval_flow_type == ApprovalFlows.ALL_REQUIRED or group is None:
            for user in User.objects.filter(user_roles__group__name=template.auto_assign_by_role,
                                            user_roles__group__tenant=tenant).distinct():
                ApproverAssignment.objects.get_or_create(
                    approval_request=request, user=user,
                    defaults=dict(is_required=True, sequence_order=final,
                                  assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP))
        else:
            GroupApproverAssignment.objects.create(
                approval_request=request, group=group, sequence_order=final,
                assignment_source=ApproverAssignmentSource.TEMPLATE_GROUP)


def describe(request) -> list[dict]:
    """The request's stages for display, in order: each with its number, whether it's
    the open one or done, and its people and groups with where they stand."""
    from Tracker.models import ApprovalDecision, TenantGroup, User
    all_stages = stages(request)
    st_open = open_stage(request)
    decisions = dict(request.responses.exclude(decision=ApprovalDecision.WITHDRAWN)
                     .values_list('approver_id', 'decision'))
    members = _members({g for st in all_stages for g in st.group_ids})
    users = {u.id: u for u in User.objects.filter(id__in={u for st in all_stages for u in st.user_ids})}
    groups = {g.id: g for g in TenantGroup.objects.filter(  # tenant-safe: the request's own groups
        id__in={g for st in all_stages for g in st.group_ids})}
    open_order = st_open.order if st_open else None
    out = []
    for n, st in enumerate(all_stages, start=1):
        rows = []
        for uid in st.user_ids:
            u = users.get(uid)
            claimed_for = [groups[g].name for g in st.group_ids
                           if uid in members.get(g, set()) and uid in st.claimed_ids and g in groups]
            rows.append({'kind': 'user', 'id': str(uid),
                         'name': (u.get_full_name() or u.get_username()) if u else str(uid),
                         'status': decisions.get(uid, 'PENDING'),
                         'for_group': claimed_for[0] if claimed_for else None})
        present = set(st.user_ids)
        for gid in st.group_ids:
            covered_by = members.get(gid, set()) & present
            rows.append({'kind': 'group', 'id': str(gid),
                         'name': groups[gid].name if gid in groups else str(gid),
                         'status': 'COVERED' if covered_by else 'PENDING', 'for_group': None})
        out.append({'number': n, 'open': st.order == open_order,
                    'done': open_order is None or st.order < open_order, 'members': rows})
    return out


def viewer_turn_refusal(request, user) -> str | None:
    """Why `user` can't answer `request` now, when the reason is the turn: they're an
    approver on it, but not in the open stage. None otherwise."""
    if request.sequence_type != 'SEQUENTIAL' or request.status != 'PENDING' or user is None:
        return None
    if not request.is_eligible_somewhere(user):
        return None
    may, _, refusal = turn(request, user)
    return None if may else refusal
