import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Separator } from "@/components/ui/separator";
import { ApprovalResponseModal } from "@/components/approval/ApprovalResponseModal";
import { useApprovalRequestsFor } from "@/hooks/useApprovalRequestsFor";
import { useAuthUser } from "@/hooks/useAuthUser";
import type { ApprovalRequest, ApprovalResponse } from "@/hooks/useDocumentApprovalRequest";
import { FileSignature, Loader2, ShieldCheck, User, Users } from "lucide-react";

/**
 * Signature-collection progress + respond affordance for any content
 * object with an attached ApprovalRequest (PCR, PCO, Documents, CAPA…).
 *
 * Extracted from the DocumentApprovalTab pattern so REGULATED-mode
 * change control reuses the exact same signature UX (drawn signature +
 * password re-entry via ApprovalResponseModal) instead of growing a
 * parallel implementation.
 *
 * Renders nothing when the object has no ApprovalRequests — callers
 * don't need to know whether signature collection has started.
 */
type Props = {
    /** Django model name, lowercase — e.g. 'processchangerequest'. */
    contentTypeModel: string;
    objectId: string | undefined;
    /** Human label for what is being signed — shown in the modal, e.g. "PCR-2026-0042". */
    contentTitle: string;
    /** Human label for the kind of artifact — e.g. "Process Change Request". */
    contentKind: string;
    title?: string;
    description?: string;
};

function isUserAnApprover(
    userId: number | string | undefined,
    userGroupIds: Array<number | string> | undefined,
    approvalRequest: ApprovalRequest | null,
): boolean {
    if (!userId || !approvalRequest) return false;
    const uid = String(userId);
    // Prefer `required_approvers_info` (objects with id) — the
    // serializer emits that, not the flat `required_approvers` array
    // the older interface assumed. Compare loosely since ids arrive as
    // numbers (User pk) here but strings (TenantGroup uuid) elsewhere.
    if (approvalRequest.required_approvers_info?.some((a) => String(a.id) === uid)) {
        return true;
    }
    if (approvalRequest.required_approvers?.some((a) => String(a) === uid)) {
        return true;
    }
    const groupIds = (userGroupIds ?? []).map(String);
    if (groupIds.length && approvalRequest.approver_groups_info?.length) {
        return approvalRequest.approver_groups_info.some((g) => groupIds.includes(String(g.id)));
    }
    if (groupIds.length && approvalRequest.approver_groups?.length) {
        return approvalRequest.approver_groups.some((g) => groupIds.includes(String(g)));
    }
    return false;
}

function hasUserResponded(userId: number | string | undefined, responses: ApprovalResponse[]): boolean {
    if (!userId || !responses) return false;
    const uid = String(userId);
    return responses.some((r) => String(r.approver) === uid);
}

export function ApprovalSignaturePanel({
    contentTypeModel,
    objectId,
    contentTitle,
    contentKind,
    title = "Approval Signatures",
    description = "Signature collection status for this change.",
}: Props) {
    const [showResponseModal, setShowResponseModal] = useState(false);
    const { data: approvalRequests, isLoading } = useApprovalRequestsFor(contentTypeModel, objectId);
    const { data: authUser } = useAuthUser();

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-6">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span className="ml-2 text-sm">Loading approval status…</span>
                </CardContent>
            </Card>
        );
    }

    const current = approvalRequests?.[0] ?? null;
    if (!current) return null;

    const pending = current.status === "PENDING" ? current : null;
    const currentUserId = authUser?.pk || authUser?.id;
    const userGroupIds = (authUser?.groups || []).map((g: { id: number }) => g.id);
    const canRespond =
        !!pending &&
        isUserAnApprover(currentUserId, userGroupIds, pending) &&
        !hasUserResponded(currentUserId, pending.responses || []);

    const respondedCount = current.responses?.filter((r) => r.decision === "APPROVED").length ?? 0;
    const requiredCount = current.required_approvers_info?.length ?? 0;

    return (
        <>
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <ShieldCheck className="h-5 w-5" />
                            {title}
                        </CardTitle>
                        <StatusBadge status={current.status} label={current.status_display || current.status} />
                    </div>
                    <CardDescription>
                        {description}
                        {requiredCount > 0 && current.status === "PENDING" && (
                            <span className="ml-1 font-medium">
                                {respondedCount} of {requiredCount} signatures collected.
                            </span>
                        )}
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-1">
                        {current.required_approvers_info?.map((approver) => {
                            const response = current.responses?.find((r) => r.approver === approver.id);
                            return (
                                <div
                                    key={approver.id}
                                    className="flex items-center justify-between text-sm p-2 rounded-lg border"
                                >
                                    <span className="flex items-center gap-2">
                                        <User className="h-4 w-4" />
                                        {approver.full_name || approver.username}
                                    </span>
                                    {response ? (
                                        <StatusBadge status={response.decision} label={response.decision_display} />
                                    ) : (
                                        <StatusBadge status="PENDING" label="Pending" />
                                    )}
                                </div>
                            );
                        })}
                        {current.approver_groups_info?.map((group) => (
                            <div
                                key={group.id}
                                className="flex items-center justify-between text-sm p-2 rounded-lg border"
                            >
                                <span className="flex items-center gap-2">
                                    <Users className="h-4 w-4" />
                                    {group.name}
                                </span>
                                <Badge variant="outline">Group</Badge>
                            </div>
                        ))}
                        {!current.required_approvers_info?.length &&
                            !current.approver_groups_info?.length && (
                                <p className="text-sm text-muted-foreground">
                                    No specific approvers assigned.
                                </p>
                            )}
                    </div>

                    {canRespond && (
                        <>
                            <Separator />
                            <div className="flex justify-end">
                                <Button onClick={() => setShowResponseModal(true)}>
                                    <FileSignature className="h-4 w-4 mr-2" />
                                    Sign / Respond
                                </Button>
                            </div>
                        </>
                    )}
                    {!canRespond && pending && (
                        <p className="text-sm text-muted-foreground">
                            {hasUserResponded(currentUserId, pending.responses || [])
                                ? "You have already submitted your response."
                                : "You are not assigned as an approver for this change."}
                        </p>
                    )}
                </CardContent>
            </Card>

            {pending && (
                <ApprovalResponseModal
                    approvalRequestId={pending.id}
                    contentTitle={contentTitle}
                    contentType={contentKind}
                    isOpen={showResponseModal}
                    onClose={() => setShowResponseModal(false)}
                />
            )}
        </>
    );
}
