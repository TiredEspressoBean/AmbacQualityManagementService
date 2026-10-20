/**
 * What holds a part at its current step, and a way past the blocks that allow one:
 * "Request bypass" raises a StepOverride for QA to approve or refuse (approve_stepoverride,
 * never the requester). An approved bypass lasts the step's override expiry. Blocks no
 * bypass clears say so — training is authorised by a supervisor at start, a life limit
 * needs a limit extension. Hidden when nothing blocks the part.
 */
import { useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { pendingBypassOptions } from "@/components/quality/BypassRequestsCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export const partBlockersOptions = (partId: string) =>
    queryOptions({
        queryKey: ["part-blockers", partId] as const,
        queryFn: () => api.api_Parts_blockers_retrieve({ params: { id: partId } }),
    });

type Blocker = { message: string; block_type: string | null };

export function PartBlockersCard({ partId }: { partId: string }) {
    const queryClient = useQueryClient();
    const canRequest = usePermissionSet().has("add_stepoverride");
    const { data } = useQuery(partBlockersOptions(partId));
    const [asking, setAsking] = useState<Blocker | null>(null);
    const [reason, setReason] = useState("");

    const request = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: (b: Blocker) => api.api_StepOverrides_create(
            { step_execution: data!.step_execution!, block_type: b.block_type as never, reason: reason.trim() },
            { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
        ),
        onSuccess: () => {
            toast.success("Bypass requested — QA will approve or refuse it");
            setAsking(null);
            setReason("");
            queryClient.invalidateQueries(partBlockersOptions(partId));
            queryClient.invalidateQueries(pendingBypassOptions());
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't request the bypass"),
    });

    const blockers = data?.blockers ?? [];
    if (blockers.length === 0) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Blocked at {data?.step_name ?? "this step"}</CardTitle>
                <CardDescription>The part can't move on until each of these clears.</CardDescription>
            </CardHeader>
            <CardContent>
                <ul className="divide-y text-sm">
                    {blockers.map((b) => (
                        <li key={b.message} className="flex flex-wrap items-center gap-2 py-2 first:pt-0 last:pb-0">
                            <span className="min-w-0 flex-1">{b.message}</span>
                            {b.bypassed ? (
                                <Badge variant="secondary">Bypass approved</Badge>
                            ) : b.request_status === "PENDING" ? (
                                <Badge variant="outline">Bypass requested — awaiting QA</Badge>
                            ) : b.block_type === null ? (
                                <span className="text-xs text-muted-foreground">No bypass for this block</span>
                            ) : (
                                <>
                                    {b.request_status === "REJECTED" && <Badge variant="destructive">Bypass refused</Badge>}
                                    {canRequest && (
                                        <Button size="sm" variant="outline" onClick={() => setAsking(b)}>
                                            Request bypass
                                        </Button>
                                    )}
                                </>
                            )}
                        </li>
                    ))}
                </ul>
            </CardContent>

            <Dialog open={asking !== null} onOpenChange={(o) => { if (!o) setAsking(null); }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Request a bypass</DialogTitle>
                        <DialogDescription>
                            {asking?.message}. QA approves or refuses it; you can&rsquo;t approve your own.
                            An approved bypass lets this part past this one block, for a limited time.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-1">
                        <Label htmlFor="bypass-reason">Why should the part move on anyway?</Label>
                        <Textarea id="bypass-reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAsking(null)}>Cancel</Button>
                        <Button disabled={!reason.trim() || request.isPending} onClick={() => asking && request.mutate(asking)}>
                            Request bypass
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
