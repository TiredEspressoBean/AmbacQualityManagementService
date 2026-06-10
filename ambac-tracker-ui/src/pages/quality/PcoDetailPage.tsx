import { useParams, useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useProcessChangeOrder, useProcessChangeRequest } from "@/hooks/useProcessChangeRequest";
import { PcrDiffViewer, type ProcessDiff } from "@/components/change-control/PcrDiffViewer";
import { PcoActions } from "@/components/change-control/PcoActions";
import { ApprovalSignaturePanel } from "@/components/approval/ApprovalSignaturePanel";
import { FileEdit, FileText } from "lucide-react";

type PcoRow = {
    id: string;
    artifact_number?: string;
    status?: string;
    request?: string;
    request_artifact_number?: string;
    request_title?: string;
    target_process_name?: string;
    draft_process_version_id?: string | null;
    implementation_plan?: string;
    effective_date?: string | null;
    migration_disposition?: string;
    migration_reason?: string;
    migrated_workorder_ids?: string[];
    approved_at?: string | null;
    approved_by_username?: string | null;
    implemented_at?: string | null;
    implemented_by_username?: string | null;
    notice_id?: string | null;
};

const STATUS_VARIANTS: Record<string, "default" | "outline" | "secondary" | "destructive"> = {
    DRAFT: "outline",
    APPROVED: "secondary",
    IMPLEMENTED: "default",
    CANCELLED: "outline",
};

export function PcoDetailPage() {
    const { id } = useParams({ strict: false }) as { id: string };
    const navigate = useNavigate();
    const { data, isLoading, error } = useProcessChangeOrder(id);
    const pco = data as PcoRow | undefined;
    const { data: pcrData } = useProcessChangeRequest(pco?.request);
    const pcr = pcrData as { proposed_change_diff?: ProcessDiff | null } | undefined;

    if (isLoading) {
        return (
            <div className="p-6 space-y-3">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-96" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    if (error || !pco) {
        return <div className="p-6"><p className="text-destructive">Could not load PCO.</p></div>;
    }

    const statusVariant = STATUS_VARIANTS[pco.status ?? ""] ?? "outline";

    return (
        <div className="p-6 space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <CardTitle className="font-mono">{pco.artifact_number}</CardTitle>
                                {pco.status && <Badge variant={statusVariant}>{pco.status}</Badge>}
                            </div>
                            <CardDescription>{pco.request_title || pco.request_artifact_number || "Process change order"}</CardDescription>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {pco.request && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => { navigate({ to: `/quality/change-control/pcrs/${pco.request}` as never }); }}
                                >
                                    <FileText className="h-4 w-4 mr-2" />
                                    Open PCR
                                </Button>
                            )}
                            {pco.draft_process_version_id && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => { navigate({ to: '/process-flow', search: { id: pco.draft_process_version_id! } as never }); }}
                                >
                                    <FileEdit className="h-4 w-4 mr-2" />
                                    Open draft
                                </Button>
                            )}
                            <PcoActions
                                pcoId={pco.id}
                                status={pco.status ?? ""}
                                implementationPlan={pco.implementation_plan}
                                effectiveDate={pco.effective_date}
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                        <div>
                            <div className="text-xs text-muted-foreground">Target process</div>
                            <div>{pco.target_process_name ?? "—"}</div>
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Source PCR</div>
                            <div className="font-mono">{pco.request_artifact_number ?? "—"}</div>
                        </div>
                        {pco.effective_date && (
                            <div>
                                <div className="text-xs text-muted-foreground">Effective date</div>
                                <div>{new Date(pco.effective_date).toLocaleDateString()}</div>
                            </div>
                        )}
                        {pco.approved_at && (
                            <div>
                                <div className="text-xs text-muted-foreground">Approved</div>
                                <div>
                                    {new Date(pco.approved_at).toLocaleString()}
                                    {pco.approved_by_username && <span className="text-muted-foreground"> by {pco.approved_by_username}</span>}
                                </div>
                            </div>
                        )}
                        {pco.implemented_at && (
                            <div>
                                <div className="text-xs text-muted-foreground">Implemented</div>
                                <div>
                                    {new Date(pco.implemented_at).toLocaleString()}
                                    {pco.implemented_by_username && <span className="text-muted-foreground"> by {pco.implemented_by_username}</span>}
                                </div>
                            </div>
                        )}
                        {pco.migration_disposition && (
                            <div>
                                <div className="text-xs text-muted-foreground">Migration disposition</div>
                                <div>{pco.migration_disposition}</div>
                            </div>
                        )}
                    </div>
                    {pco.implementation_plan && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Implementation plan</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pco.implementation_plan}</div>
                        </div>
                    )}
                    {pco.migration_reason && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Migration reason</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pco.migration_reason}</div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Signature collection — renders only once the PCO has been
                submitted for signatures (REGULATED). The cascade flips the
                PCO to APPROVED when the last required signature lands. */}
            <ApprovalSignaturePanel
                contentTypeModel="processchangeorder"
                objectId={pco.id}
                contentTitle={pco.artifact_number ?? pco.id}
                contentKind="Process Change Order"
            />

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Changes (from PCR)</CardTitle>
                    <CardDescription>Structured diff inherited from the source request.</CardDescription>
                </CardHeader>
                <CardContent>
                    <PcrDiffViewer diff={pcr?.proposed_change_diff ?? null} />
                </CardContent>
            </Card>
        </div>
    );
}
