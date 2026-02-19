import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ApprovalResponseModal } from "@/components/approval/ApprovalResponseModal";
import { useSubmitDocumentForApproval } from "@/hooks/useSubmitDocumentForApproval";
import { useDocumentApprovalRequest, type ApprovalRequest, type ApprovalResponse } from "@/hooks/useDocumentApprovalRequest";
import { useAuthUser } from "@/hooks/useAuthUser";
import {
    CheckCircle2,
    XCircle,
    Clock,
    AlertTriangle,
    ShieldCheck,
    User,
    Calendar,
    Loader2,
    FileSignature,
    Users,
    Send,
} from "lucide-react";

type DocumentApprovalTabProps = {
    document: any;
};

function isUserAnApprover(
    userId: number | undefined,
    userGroupIds: number[] | undefined,
    approvalRequest: ApprovalRequest | null
): boolean {
    if (!userId || !approvalRequest) return false;

    if (approvalRequest.required_approvers?.includes(userId)) {
        return true;
    }

    if (userGroupIds && approvalRequest.approver_groups?.length) {
        const hasMatchingGroup = userGroupIds.some(groupId =>
            approvalRequest.approver_groups.includes(groupId)
        );
        if (hasMatchingGroup) return true;
    }

    return false;
}

function hasUserResponded(userId: number | undefined, responses: ApprovalResponse[]): boolean {
    if (!userId || !responses) return false;
    return responses.some(r => r.approver === userId);
}

export function DocumentApprovalTab({ document }: DocumentApprovalTabProps) {
    const [showResponseModal, setShowResponseModal] = useState(false);
    const { mutate: submitForApproval, isPending: isSubmitting } = useSubmitDocumentForApproval(document.id);
    const { data: approvalRequests, isLoading: loadingApprovals } = useDocumentApprovalRequest(document.id);
    const { data: authUser } = useAuthUser();

    const status = document.status;
    const isDraft = status === 'DRAFT';
    const isUnderReview = status === 'UNDER_REVIEW';
    const isApproved = status === 'APPROVED' || status === 'RELEASED';

    // Get the most recent approval request
    const currentApprovalRequest = approvalRequests?.[0] || null;
    const pendingApprovalRequest = approvalRequests?.find(r => r.status === 'PENDING') || null;

    // Check if current user can respond
    const currentUserId = authUser?.pk || authUser?.id;
    // Extract group IDs from group objects
    const userGroupIds = (authUser?.groups || []).map((g) => g.id);
    const canRespond = isUserAnApprover(currentUserId, userGroupIds, pendingApprovalRequest) &&
        !hasUserResponded(currentUserId, pendingApprovalRequest?.responses || []);

    const handleSubmitForApproval = () => {
        submitForApproval(undefined, {
            onSuccess: () => {
                // Refresh will happen via query invalidation
            },
        });
    };

    // Draft status - can submit for approval
    if (isDraft) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5" />
                        Submit for Approval
                    </CardTitle>
                    <CardDescription>
                        This document is in Draft status and can be submitted for approval
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Alert>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Document Not Yet Submitted</AlertTitle>
                        <AlertDescription>
                            Submit this document for approval to begin the review process.
                            Once submitted, designated approvers will be notified to review.
                        </AlertDescription>
                    </Alert>

                    <Button onClick={handleSubmitForApproval} disabled={isSubmitting}>
                        {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        <Send className="h-4 w-4 mr-2" />
                        Submit for Approval
                    </Button>
                </CardContent>
            </Card>
        );
    }

    if (loadingApprovals) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading approval details...</span>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            {/* Approval Status Card */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <ShieldCheck className="h-5 w-5" />
                            Approval Status
                        </CardTitle>
                        <StatusBadge
                            status={document.status}
                            label={document.status_display || document.status}
                        />
                    </div>
                    <CardDescription>
                        Document approval workflow status
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Under Review State */}
                    {isUnderReview && (
                        <>
                            <Alert>
                                <Clock className="h-4 w-4" />
                                <AlertTitle>Under Review</AlertTitle>
                                <AlertDescription>
                                    This document is pending approval review.
                                </AlertDescription>
                            </Alert>

                            {/* Show assigned approvers */}
                            {pendingApprovalRequest && (
                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium flex items-center gap-2">
                                        <Users className="h-4 w-4" />
                                        Assigned Approvers
                                    </h4>
                                    <div className="space-y-1">
                                        {pendingApprovalRequest.required_approvers_info?.map((approver) => {
                                            const hasResponded = pendingApprovalRequest.responses?.some(
                                                r => r.approver === approver.id
                                            );
                                            const response = pendingApprovalRequest.responses?.find(
                                                r => r.approver === approver.id
                                            );
                                            return (
                                                <div key={approver.id} className="flex items-center justify-between text-sm p-2 rounded-lg border">
                                                    <span className="flex items-center gap-2">
                                                        <User className="h-4 w-4" />
                                                        {approver.full_name || approver.username}
                                                    </span>
                                                    {hasResponded && response ? (
                                                        <StatusBadge
                                                            status={response.decision}
                                                            label={response.decision_display}
                                                        />
                                                    ) : (
                                                        <StatusBadge
                                                            status="PENDING"
                                                            label="Pending"
                                                        />
                                                    )}
                                                </div>
                                            );
                                        })}
                                        {pendingApprovalRequest.approver_groups_info?.map((group) => (
                                            <div key={group.id} className="flex items-center justify-between text-sm p-2 rounded-lg border">
                                                <span className="flex items-center gap-2">
                                                    <Users className="h-4 w-4" />
                                                    {group.name}
                                                </span>
                                                <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                                                    Group
                                                </Badge>
                                            </div>
                                        ))}
                                        {!pendingApprovalRequest.required_approvers_info?.length &&
                                            !pendingApprovalRequest.approver_groups_info?.length && (
                                                <p className="text-sm text-muted-foreground">
                                                    No specific approvers assigned.
                                                </p>
                                            )}
                                    </div>
                                </div>
                            )}

                            {/* Action button for approvers */}
                            {canRespond && (
                                <>
                                    <Separator />
                                    <div className="flex justify-end">
                                        <Button onClick={() => setShowResponseModal(true)}>
                                            <FileSignature className="h-4 w-4 mr-2" />
                                            Submit Response
                                        </Button>
                                    </div>
                                </>
                            )}

                            {!canRespond && pendingApprovalRequest && (
                                <p className="text-sm text-muted-foreground">
                                    {hasUserResponded(currentUserId, pendingApprovalRequest.responses || [])
                                        ? "You have already submitted your response."
                                        : "You are not assigned as an approver for this document."}
                                </p>
                            )}
                        </>
                    )}

                    {/* Approved State */}
                    {isApproved && (
                        <div className="space-y-4">
                            <Alert className="border-green-200 bg-green-50">
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                                <AlertTitle className="text-green-800">Approved</AlertTitle>
                                <AlertDescription className="text-green-700">
                                    This document has been approved and is ready for use.
                                </AlertDescription>
                            </Alert>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-muted-foreground flex items-center gap-1">
                                        <User className="h-4 w-4" />
                                        Approved By
                                    </span>
                                    <p className="font-medium">
                                        {document.approved_by_name ||
                                            currentApprovalRequest?.responses?.find(r => r.decision === 'APPROVED')
                                                ?.approver_info?.full_name ||
                                            "—"}
                                    </p>
                                </div>
                                <div>
                                    <span className="text-muted-foreground flex items-center gap-1">
                                        <Calendar className="h-4 w-4" />
                                        Approved At
                                    </span>
                                    <p className="font-medium">
                                        {document.approved_at
                                            ? new Date(document.approved_at).toLocaleString()
                                            : currentApprovalRequest?.completed_at
                                                ? new Date(currentApprovalRequest.completed_at).toLocaleString()
                                                : "—"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Obsolete State */}
                    {status === 'OBSOLETE' && (
                        <Alert variant="destructive">
                            <XCircle className="h-4 w-4" />
                            <AlertTitle>Obsolete</AlertTitle>
                            <AlertDescription>
                                This document has been marked as obsolete and should no longer be used.
                            </AlertDescription>
                        </Alert>
                    )}
                </CardContent>
            </Card>

            {/* Approval History Card */}
            <Card>
                <CardHeader>
                    <CardTitle>Approval History</CardTitle>
                    <CardDescription>Record of all approval responses</CardDescription>
                </CardHeader>
                <CardContent>
                    {!approvalRequests?.length || approvalRequests.every(req => !req.responses?.length) ? (
                        <p className="text-sm text-muted-foreground">No approval history yet.</p>
                    ) : (
                        <div className="space-y-4">
                            {approvalRequests?.map((request) => (
                                <div key={request.id} className="space-y-2">
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="font-medium">
                                            Request #{request.approval_number}
                                        </span>
                                        <StatusBadge
                                            status={request.status}
                                            label={request.status_display}
                                        />
                                    </div>
                                    {request.responses?.map((response) => (
                                        <div key={response.id} className="flex items-start gap-3 p-3 border rounded-lg ml-4">
                                            {response.decision === 'APPROVED' ? (
                                                <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                                            ) : response.decision === 'REJECTED' ? (
                                                <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                                            ) : (
                                                <User className="h-5 w-5 text-blue-600 mt-0.5" />
                                            )}
                                            <div className="flex-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium">
                                                        {response.approver_info?.full_name || response.approver_info?.username}
                                                    </span>
                                                    <span className="text-sm text-muted-foreground">
                                                        {new Date(response.decision_date).toLocaleString()}
                                                    </span>
                                                </div>
                                                <StatusBadge
                                                    status={response.decision}
                                                    label={response.decision_display}
                                                />
                                                {response.comments && (
                                                    <p className="text-sm text-muted-foreground mt-2">
                                                        {response.comments}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Approval Response Modal */}
            {pendingApprovalRequest && (
                <ApprovalResponseModal
                    approvalRequestId={pendingApprovalRequest.id}
                    contentTitle={document.file_name}
                    contentType="Document Approval"
                    isOpen={showResponseModal}
                    onClose={() => setShowResponseModal(false)}
                />
            )}
        </div>
    );
}
