import { useParams, useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useProcessChangeNotice } from "@/hooks/useProcessChangeRequest";
import { PcnActions } from "@/components/change-control/PcnActions";
import { FileText } from "lucide-react";

type PcnRow = {
    id: string;
    artifact_number?: string;
    status?: string;
    order?: string;
    order_artifact_number?: string;
    pcr_artifact_number?: string;
    target_process_name?: string;
    notice_content?: string;
    released_at?: string | null;
    released_by_username?: string | null;
    closure_evidence?: string;
    closed_at?: string | null;
    closed_by_username?: string | null;
};

const STATUS_VARIANTS: Record<string, "default" | "outline" | "secondary" | "destructive"> = {
    DRAFT: "outline",
    RELEASED: "secondary",
    ACKNOWLEDGED: "default",
    CLOSED: "default",
};

export function PcnDetailPage() {
    const { id } = useParams({ strict: false }) as { id: string };
    const navigate = useNavigate();
    const { data, isLoading, error } = useProcessChangeNotice(id);

    if (isLoading) {
        return (
            <div className="p-6 space-y-3">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    if (error || !data) {
        return <div className="p-6"><p className="text-destructive">Could not load PCN.</p></div>;
    }

    const pcn = data as PcnRow;
    const statusVariant = STATUS_VARIANTS[pcn.status ?? ""] ?? "outline";

    return (
        <div className="p-6 space-y-4">
            <Card>
                <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <CardTitle className="font-mono">{pcn.artifact_number}</CardTitle>
                                {pcn.status && <Badge variant={statusVariant}>{pcn.status}</Badge>}
                            </div>
                            <CardDescription>
                                {pcn.target_process_name ?? "Process change notice"}
                            </CardDescription>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {pcn.order && (
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => { navigate({ to: `/quality/change-control/pcos/${pcn.order}` as never }); }}
                                >
                                    <FileText className="h-4 w-4 mr-2" />
                                    Open PCO
                                </Button>
                            )}
                            <PcnActions pcnId={pcn.id} status={pcn.status ?? ""} />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                        <div>
                            <div className="text-xs text-muted-foreground">Source PCO</div>
                            <div className="font-mono">{pcn.order_artifact_number ?? "—"}</div>
                        </div>
                        <div>
                            <div className="text-xs text-muted-foreground">Originating PCR</div>
                            <div className="font-mono">{pcn.pcr_artifact_number ?? "—"}</div>
                        </div>
                        {pcn.released_at && (
                            <div>
                                <div className="text-xs text-muted-foreground">Released</div>
                                <div>
                                    {new Date(pcn.released_at).toLocaleString()}
                                    {pcn.released_by_username && <span className="text-muted-foreground"> by {pcn.released_by_username}</span>}
                                </div>
                            </div>
                        )}
                        {pcn.closed_at && (
                            <div>
                                <div className="text-xs text-muted-foreground">Closed</div>
                                <div>
                                    {new Date(pcn.closed_at).toLocaleString()}
                                    {pcn.closed_by_username && <span className="text-muted-foreground"> by {pcn.closed_by_username}</span>}
                                </div>
                            </div>
                        )}
                    </div>

                    {pcn.notice_content && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Notice content</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pcn.notice_content}</div>
                        </div>
                    )}
                    {pcn.closure_evidence && (
                        <div>
                            <div className="text-xs text-muted-foreground mb-1">Closure evidence</div>
                            <div className="whitespace-pre-wrap rounded-md bg-muted/30 p-3">{pcn.closure_evidence}</div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
