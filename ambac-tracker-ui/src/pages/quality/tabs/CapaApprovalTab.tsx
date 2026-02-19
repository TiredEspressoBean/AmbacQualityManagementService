import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ApprovalResponseModal } from "@/components/approval/ApprovalResponseModal";
import { useRequestCapaApproval } from "@/hooks/useRequestCapaApproval";
import { useCapaApprovalRequest, type ApprovalRequest, type ApprovalResponse } from "@/hooks/useCapaApprovalRequest";
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
} from "lucide-react";

type CapaApprovalTabProps = {
    capa: any;
};

function isUserAnApprover(
    userId: number | undefined,
    userGroupIds: number[] | undefined,
    approvalRequest: ApprovalRequest | null
): boolean {
    if (!userId || !approvalRequest) return false;

    // Check if user is in required_approvers
    if (approvalRequest.required_approvers?.includes(userId)) {
        return true;
    }

    // Check if user's group is in approver_groups
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

export function CapaApprovalTab({ capa }: CapaApprovalTabProps) {
    const [showResponseModal, setShowResponseModal] = useState(false);
    const { mutate: requestApproval, isPending: isRequesting } = useRequestCapaApproval(capa?.id);
    const { data: approvalRequests, isLoading: loadingApprovals } = useCapaApprovalRequest(capa?.id);
    const { data: authUser } = useAuthUser();

    if (!capa) {
        return null;
    }

    const approvalRequired = capa?.approval_required;
    const approvalStatus = capa?.approval_status || 'NOT_REQUIRED';
    const severity = capa?.severity;
    const requiresApprovalBySeverity = severity === 'CRITICAL' || severity === 'MAJOR';

    // Get the most recent (usually pending) approval request
    const currentApprovalRequest = approvalRequests?.[0] || null;
    const pendingApprovalRequest = approvalRequests?.find(r => r.status === 'PENDING') || null;

    // Check if current user can respond
    const currentUserId = authUser?.pk || authUser?.id;
    // Extract group IDs from group objects
    const userGroupIds = (authUser?.groups || []).map((g) => g.id);
    const canRespond = isUserAnApprover(currentUserId, userGroupIds, pendingApprovalRequest) &&
        !hasUserResponded(currentUserId, pendingApprovalRequest?.responses || []);

    const handleRequestApproval = () => {
        requestApproval(undefined, {
            onSuccess: () => {
                // Refresh will happen via query invalidation
            },
        });
    };

    // No approval required for MINOR severity
    if (!requiresApprovalBySeverity && !approvalRequired) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5" />
                        Approval Status
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Alert>
                        <CheckCircle2 className="h-4 w-4" />
                        <AlertTitle>No Approval Required</AlertTitle>
                        <AlertDescription>
                            This CAPA has <strong>{capa?.severity_display}</strong> severity and does not require management approval.
                        </AlertDescription>
                    </Alert>
                </CardContent>
            </Card>
        );
    }

    // Approval required but not yet requested
    if (requiresApprovalBySeverity && !approvalRequired && approvalStatus !== 'APPROVED') {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5" />
                        Approval Required
                    </CardTitle>
                    <CardDescription>
                        This CAPA requires management approval due to {capa?.severity_display} severity
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Approval Not Yet Requested</AlertTitle>
                        <AlertDescription>
                            CAPAs with {capa?.severity_display} severity require management approval before work can begin.
                            Please request approval to proceed.
                        </AlertDescription>
                    </Alert>

                    <Button onClick={handleRequestApproval} disabled={isRequesting}>
                        {isRequesting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        <FileSignature className="h-4 w-4 mr-2" />
                        Request Approval
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
                        <StatusBadge status={approvalStatus} label={capa.approval_status_display || approvalStatus} />
                    </div>
                    <CardDescription>
                        Management approval for {capa?.severity_display} severity CAPA
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Pending State */}
                    {approvalStatus === 'PENDING' && (
                        <>
                            <Alert>
                                <Clock className="h-4 w-4" />
                                <AlertTitle>Awaiting Approval</AlertTitle>
                                <AlertDescription>
                                    This CAPA is pending management approval. Work cannot begin until approved.
                                </AlertDescription>
                            </Alert>

                            {/* Show assigned approvers from ApprovalRequest */}
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
                                                        <StatusBadge status={response.decision} label={response.decision_display} />
                                                    ) : (
                                                        <StatusBadge status="PENDING" label="Pending" />
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
                                                    No specific approvers assigned. QA Management will review.
                                                </p>
                                            )}
                                    </div>
                                </div>
                            )}

                            {/* Action button - show only if current user is an approver and hasn't responded */}
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

                            {/* Show hint if user is not an approver */}
                            {!canRespond && pendingApprovalRequest && (
                                <p className="text-sm text-muted-foreground">
                                    {hasUserResponded(currentUserId, pendingApprovalRequest.responses || [])
                                        ? "You have already submitted your response."
                                        : "You are not assigned as an approver for this request."}
                                </p>
                            )}
                        </>
                    )}

                    {/* Approved State */}
                    {approvalStatus === 'APPROVED' && (
                        <div className="space-y-4">
                            <Alert className="border-green-200 bg-green-50">
                                <CheckCircle2 className="h-4 w-4 text-green-600" />
                                <AlertTitle className="text-green-800">Approved</AlertTitle>
                                <AlertDescription className="text-green-700">
                                    This CAPA has been approved. Work may proceed.
                                </AlertDescription>
                            </Alert>

                            {currentApprovalRequest && (
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="text-muted-foreground flex items-center gap-1">
                                            <User className="h-4 w-4" />
                                            Approved By
                                        </span>
                                        <p className="font-medium">
                                            {currentApprovalRequest.responses?.find(r => r.decision === 'APPROVED')
                                                ?.approver_info?.full_name ||
                                                currentApprovalRequest.responses?.find(r => r.decision === 'APPROVED')
                                                    ?.approver_info?.username ||
                                                capa?.approved_by_info?.full_name ||
                                                capa?.approved_by_info?.username ||
                                                "—"}
                                        </p>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground flex items-center gap-1">
                                            <Calendar className="h-4 w-4" />
                                            Approved At
                                        </span>
                                        <p className="font-medium">
                                            {currentApprovalRequest.completed_at
                                                ? new Date(currentApprovalRequest.completed_at).toLocaleString()
                                                : capa?.approved_at
                                                    ? new Date(capa.approved_at).toLocaleString()
                                                    : "—"}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Rejected State */}
                    {approvalStatus === 'REJECTED' && (
                        <div className="space-y-4">
                            <Alert variant="destructive">
                                <XCircle className="h-4 w-4" />
                                <AlertTitle>Rejected</AlertTitle>
                                <AlertDescription>
                                    This CAPA was rejected. Please review the feedback and make necessary changes.
                                </AlertDescription>
                            </Alert>

                            {currentApprovalRequest && (
                                <>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-muted-foreground">Rejected By</span>
                                            <p className="font-medium">
                                                {currentApprovalRequest.responses?.find(r => r.decision === 'REJECTED')
                                                    ?.approver_info?.full_name ||
                                                    currentApprovalRequest.responses?.find(r => r.decision === 'REJECTED')
                                                        ?.approver_info?.username ||
                                                    "—"}
                                            </p>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Rejected At</span>
                                            <p className="font-medium">
                                                {currentApprovalRequest.completed_at
                                                    ? new Date(currentApprovalRequest.completed_at).toLocaleString()
                                                    : "—"}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Show rejection comments */}
                                    {currentApprovalRequest.responses?.find(r => r.decision === 'REJECTED')?.comments && (
                                        <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                                            <p className="text-sm font-medium text-red-800 mb-1">Rejection Reason:</p>
                                            <p className="text-sm text-red-700">
                                                {currentApprovalRequest.responses.find(r => r.decision === 'REJECTED')?.comments}
                                            </p>
                                        </div>
                                    )}
                                </>
                            )}

                            <Separator />

                            <Button variant="outline" onClick={handleRequestApproval} disabled={isRequesting}>
                                {isRequesting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                Request Re-Approval
                            </Button>
                        </div>
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
                                        <StatusBadge status={request.status} label={request.status_display} />
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
                                                <StatusBadge status={response.decision} label={response.decision_display} />
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
                    contentTitle={capa?.capa_number}
                    contentType="CAPA Approval"
                    isOpen={showResponseModal}
                    onClose={() => setShowResponseModal(false)}
                />
            )}
        </div>
    );
}
