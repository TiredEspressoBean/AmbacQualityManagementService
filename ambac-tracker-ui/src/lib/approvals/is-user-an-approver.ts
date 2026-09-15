/**
 * "Is this user allowed to respond to this approval request?"
 *
 * One implementation, because there were three and they disagreed.
 * ApprovalSignaturePanel (change control) had the correct version;
 * CapaApprovalTab had it half-right; DocumentApprovalTab had the original,
 * which checked only `required_approvers` — a field the API does not emit.
 * That returned false for everyone, so the document approval panel listed the
 * assigned approvers and simultaneously told each of them they were not an
 * approver, and no document could be approved through the UI.
 *
 * The trap: `ApprovalRequestSerializer` emits `required_approvers_info` and
 * `approver_groups_info` (objects with ids), plus the flat `approver_groups`
 * uuid list. There is no flat `required_approvers`. Three hand-written
 * `ApprovalRequest` interfaces declared one anyway — with two different types
 * between them — which is why reading it type-checked clean.
 *
 * Ids are compared as strings throughout: User pks arrive as numbers,
 * TenantGroup ids as uuids, and callers hold either.
 */

/** Only what the check needs — every caller's ApprovalRequest shape satisfies it. */
export type ApproverFields = {
    required_approvers_info?: Array<{ id?: number | string }> | null;
    /** Legacy flat id list. The API does not send it; kept so a caller that
     *  still declares it is honoured rather than silently ignored. */
    required_approvers?: Array<number | string> | null;
    approver_groups_info?: Array<{ id?: number | string }> | null;
    approver_groups?: Array<number | string> | null;
};

export function isUserAnApprover(
    userId: number | string | undefined,
    userGroupIds: Array<number | string> | undefined,
    approvalRequest: ApproverFields | null | undefined,
): boolean {
    if (!userId || !approvalRequest) return false;
    const uid = String(userId);

    // Direct assignment — `_info` first, since that is what the API sends.
    if (approvalRequest.required_approvers_info?.some((a) => String(a?.id) === uid)) return true;
    if (approvalRequest.required_approvers?.some((a) => String(a) === uid)) return true;

    // Group assignment — same order, same reason.
    const groupIds = (userGroupIds ?? []).map(String);
    if (!groupIds.length) return false;
    if (approvalRequest.approver_groups_info?.some((g) => groupIds.includes(String(g?.id)))) return true;
    if (approvalRequest.approver_groups?.some((g) => groupIds.includes(String(g)))) return true;

    return false;
}
