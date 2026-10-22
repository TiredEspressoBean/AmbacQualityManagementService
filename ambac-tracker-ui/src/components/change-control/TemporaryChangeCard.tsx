import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarClock } from "lucide-react";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { parseDateOnly } from "@/lib/date-only";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export type TemporaryInfo = {
    version_id: string;
    version: number;
    until: string | null;
    expired: boolean;
    work_orders: { id: string; erp_id: string; status: string }[];
};

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

/**
 * A temporary change (deviation) in force: its end date, the work orders on it, and the
 * two ways out of an expiry — a PCR that extends it, or moving a work order back to the
 * baseline (services/change_control/temporary.py).
 */
export function TemporaryChangeCard({ pcrId, artifactNumber, info }: {
    pcrId: string;
    artifactNumber: string;
    info: TemporaryInfo;
}) {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { has } = usePermissionSet();
    const [extendOpen, setExtendOpen] = useState(false);
    const [until, setUntil] = useState("");
    const [justification, setJustification] = useState("");

    const refresh = () => queryClient.invalidateQueries({
        predicate: (q) => JSON.stringify(q.queryKey).includes(pcrId),
    });

    const extend = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: () => api.api_process_change_requests_extend_create(
            { temporary_until: until, justification },
            { params: { id: pcrId }, headers: csrf() },
        ),
        onSuccess: (extension) => {
            toast.success(`${extension.artifact_number} raised — submit it for approval`);
            setExtendOpen(false);
            navigate({ to: "/quality/change-control/pcrs/$id", params: { id: extension.id } });
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't raise the extension"),
    });

    const moveBack = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (workOrder: string) => api.api_process_change_requests_return_to_baseline_create(
            { work_order: workOrder },
            { params: { id: pcrId }, headers: csrf() },
        ),
        onSuccess: () => {
            toast.success("Work order moved back to the baseline");
            refresh();
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't move the work order back"),
    });

    const untilLabel = info.until ? parseDateOnly(info.until).toLocaleDateString() : "—";
    const open = info.work_orders.filter((w) => w.status !== "COMPLETED" && w.status !== "CANCELLED");

    return (
        <Card className={info.expired ? "border-destructive/50" : "border-amber-500/40"}>
            <CardHeader>
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <CardTitle className="text-base flex items-center gap-2">
                            <CalendarClock className="h-4 w-4" />
                            Temporary change
                            {info.expired
                                ? <Badge variant="destructive">Ended {untilLabel}</Badge>
                                : <Badge variant="outline">Until {untilLabel}</Badge>}
                        </CardTitle>
                        <CardDescription>
                            In force for the work orders below only; the current version stays in force
                            for everything else.{info.expired
                                ? " It has ended, so their work can't proceed until it is extended or they go back."
                                : ""}
                        </CardDescription>
                    </div>
                    {has("add_processchangerequest") && open.length > 0 && (
                        <Button variant="outline" size="sm" onClick={() => { setUntil(""); setJustification(""); setExtendOpen(true); }}>
                            Extend…
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {info.work_orders.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No work orders are on it now.</p>
                ) : (
                    <div className="divide-y">
                        {info.work_orders.map((w) => (
                            <div key={w.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                                <Link to="/workorder/$workOrderId" params={{ workOrderId: w.id }} className="font-mono hover:underline">
                                    {w.erp_id}
                                </Link>
                                <span className="text-xs text-muted-foreground">{w.status.replace(/_/g, " ").toLowerCase()}</span>
                                <span className="ml-auto">
                                    {has("change_processchangeorder") && w.status !== "COMPLETED" && w.status !== "CANCELLED" && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            disabled={moveBack.isPending}
                                            // It changes the routing the work order runs on — say
                                            // so first (Engineering walk: it went straight through).
                                            onClick={() => {
                                                if (window.confirm(`Move ${w.erp_id} back to the baseline routing? Its remaining steps follow the baseline, not the temporary change.`)) {
                                                    moveBack.mutate(w.id);
                                                }
                                            }}
                                        >
                                            Move back to baseline
                                        </Button>
                                    )}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>

            <Dialog open={extendOpen} onOpenChange={setExtendOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Extend {artifactNumber}</DialogTitle>
                        <DialogDescription>
                            Raises a change request that moves the end date. It is approved and implemented
                            like any other change; until then the current date stands.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label htmlFor="extend-until">New end date</Label>
                            <Input id="extend-until" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
                        </div>
                        <div>
                            <Label htmlFor="extend-why">Why it is still needed</Label>
                            <Textarea id="extend-why" value={justification} onChange={(e) => setJustification(e.target.value)} rows={3} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setExtendOpen(false)}>Cancel</Button>
                        <Button disabled={!until || extend.isPending} onClick={() => extend.mutate()}>
                            Raise extension
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
