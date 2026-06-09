import { useParams, useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useProcessChangeRequest } from "@/hooks/useProcessChangeRequest";
import { PcrDiffViewer, type ProcessDiff } from "@/components/change-control/PcrDiffViewer";
import { PcrActions } from "@/components/change-control/PcrActions";
import { FileEdit } from "lucide-react";

type PcrRow = {
    id: string;
    artifact_number?: string;
    status?: string;
    priority?: string;
    title?: string;
    proposed_change?: string;
    justification?: string;
    risk_analysis?: string;
    target_process?: string;
    target_process_name?: string;
    draft_process_version?: string | null;
    proposed_change_diff?: ProcessDiff | null;
    created_at?: string;
    created_by_username?: string | null;
    submitted_at?: string | null;
    submitted_by_username?: string | null;
    customer_notification_required?: boolean;
    rejected_reason?: string;
    affected_workorders_count?: number;
};

const STATUS_VARIANTS: Record<string, "default" | "outline" | "secondary" | "destructive"> = {
    DRAFT: "outline",
    SUBMITTED: "secondary",
    UNDER_REVIEW: "secondary",
    APPROVED: "default",
    REJECTED: "destructive",
    CANCELLED: "outline",
};

export function PcrDetailPage() {
    const { id } = useParams({ strict: false }) as { id: string };
    const navigate = useNavigate();
    const { data, isLoading, error } = useProcessChangeRequest(id);

    if (isLoading) {
        return (
            <div className="p-6 space-y-3">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-96" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="p-6">
                <p className="text-destructive">Could not load PCR.</p>
            </div>
        );
    }

    const pcr = data as PcrRow;
    const statusVariant = STATUS_VARIANTS[pcr.status ?? ""] ?? "outline";

    return (
        <div className="p-6 space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <CardTitle className="font-mono">{pcr.artifact_number}</CardTitle>
                                {pcr.status && <Badge variant={statusVariant}>{pcr.status}</Badge>}
                                {pcr.priority && pcr.priority !== "NORMAL" && (
                                    <Badge variant="outline">{pcr.priority}</Badge>
                                )}
                            </div>
                            <CardDescription>
                                {pcr.title || <span className="italic">No title</span>}
                            </CardDescription>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {pcr.draft_process_version && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => { navigate({ to: '/process-flow', search: { id: pcr.draft_process_version! } as never }); }}
                                >
                                    <FileEdit className="h-4 w-4 mr-2" />
                                    Open draft
                                </Button>
                            )}
                            <PcrActions pcrId={pcr.id} status={pcr.status ?? ""} />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                        <div>
                            <div className="text-xs text-muted-foreground">Target process</div>
                            <div>{pcr.target_process_name ?? pcr.target_process ?? "—"}</div>
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Created</div>
                            <div>
                                {pcr.created_at ? new Date(pcr.created_at).toLocaleString() : "—"}
                                {pcr.created_by_username && <span className="text-muted-foreground"> by {pcr.created_by_username}</span>}
                            </div>
                        </div>
                        {pcr.submitted_at && (
                            <div>
                                <div className="text-xs text-muted-foreground">Submitted</div>
                                <div>
                                    {new Date(pcr.submitted_at).toLocaleString()}
                                    {pcr.submitted_by_username && <span className="text-muted-foreground"> by {pcr.submitted_by_username}</span>}
                                </div>
                            </div>
                        )}
                        {typeof pcr.affected_workorders_count === "number" && (
                            <div>
                                <div className="text-xs text-muted-foreground">Affected in-flight WOs</div>
                                <div>{pcr.affected_workorders_count}</div>
                            </div>
                        )}
                    </div>

                    {pcr.proposed_change && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Proposed change</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pcr.proposed_change}</div>
                        </div>
                    )}
                    {pcr.justification && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Justification</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pcr.justification}</div>
                        </div>
                    )}
                    {pcr.risk_analysis && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Risk analysis</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pcr.risk_analysis}</div>
                        </div>
                    )}
                    {pcr.rejected_reason && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Rejection reason</div>
                            <div className="whitespace-pre-wrap rounded-md bg-destructive/10 p-3">{pcr.rejected_reason}</div>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Proposed changes</CardTitle>
                    <CardDescription>Structured diff between the approved baseline and the draft.</CardDescription>
                </CardHeader>
                <CardContent>
                    <PcrDiffViewer diff={pcr.proposed_change_diff ?? null} />
                </CardContent>
            </Card>
        </div>
    );
}
