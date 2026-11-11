/**
 * An item's life: each limit it's tracked against — used, soft and hard limit, status —
 * with Reset (after refurbishment, a reason required) and Extend (an approved higher
 * limit) per tracking (user ruling 2026-11-11). Both are life-limit authority
 * (`change_lifelimitdefinition`). A refusal at Start Work and the tool's soft-limit
 * notification send people here.
 *
 * Only trackings against the CURRENT version of a limit decide anything; those against
 * a superseded version are kept for the record and folded under "earlier versions".
 */
import { useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { getCookie } from "@/lib/utils";
import { usePermissionSet } from "@/hooks/useMyPermissions";

const trackingsOptions = (contentType: string, objectId: string) => queryOptions({
    queryKey: ["life-tracking", contentType, objectId] as const,
    queryFn: () => api.api_LifeTracking_for_object_list({
        queries: { content_type: contentType, object_id: objectId },
    }),
});

type Tracking = Awaited<ReturnType<typeof api.api_LifeTracking_for_object_list>>[number];

/** 2.00 → "2"; null → "—". */
function n(v: string | number | null | undefined): string {
    if (v === null || v === undefined || v === "") return "—";
    const x = Number(v);
    return Number.isFinite(x) ? String(+x.toFixed(2)) : String(v);
}

const STATUS_VARIANT: Record<string, "secondary" | "outline" | "destructive"> = {
    OK: "outline", WARNING: "secondary", EXPIRED: "destructive",
};

export function LifeTrackingSection({ contentType, objectId }: {
    /** "tracker.equipments" or "tracker.parts". */
    contentType: string;
    objectId: string;
}) {
    const qc = useQueryClient();
    const { has } = usePermissionSet();
    const canAct = has("change_lifelimitdefinition");
    const { data: rows = [] } = useQuery(trackingsOptions(contentType, objectId));
    const current = rows.filter((t) => t.definition_is_current);
    const earlier = rows.filter((t) => !t.definition_is_current);

    const [acting, setActing] = useState<{ t: Tracking; kind: "reset" | "extend" } | null>(null);
    const [reason, setReason] = useState("");
    const [hard, setHard] = useState("");
    const close = () => { setActing(null); setReason(""); setHard(""); };
    const headers = { "X-CSRFToken": getCookie("csrftoken") ?? "" };

    const act = useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: async () => {
            if (!acting) return;
            const id = String(acting.t.id);
            if (acting.kind === "reset") {
                await api.api_LifeTracking_reset_create({ reason }, { params: { id }, headers });
            } else {
                await api.api_LifeTracking_apply_override_create(
                    { hard_limit: hard, reason }, { params: { id }, headers });
            }
        },
        onSuccess: () => {
            toast.success(acting?.kind === "reset" ? "Life reset" : "Limit extended");
            void qc.invalidateQueries(trackingsOptions(contentType, objectId));
            close();
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "That didn't go through"),
    });

    if (rows.length === 0) return null;

    const row = (t: Tracking) => (
        <div key={String(t.id)} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b py-2 last:border-b-0">
            <div className="min-w-40 font-medium">{t.definition_name}</div>
            <div className="text-sm">
                {n(t.current_value)} used · soft {n(t.effective_soft_limit)} · hard {n(t.effective_hard_limit)}
                {t.definition_unit ? ` ${t.definition_unit.toLowerCase()}` : ""}
            </div>
            <Badge variant={STATUS_VARIANT[t.status] ?? "outline"}>{t.status}</Badge>
            {t.definition_is_current && canAct && (
                <div className="ml-auto flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setActing({ t, kind: "reset" })}>
                        Reset
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => {
                        setHard(t.effective_hard_limit != null ? n(t.effective_hard_limit) : "");
                        setActing({ t, kind: "extend" });
                    }}>
                        Extend
                    </Button>
                </div>
            )}
        </div>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Life</CardTitle>
                <CardDescription>
                    What it has used against each limit. At the hard limit no work starts with
                    it until it's reset after refurbishment or an extension is approved.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {current.map(row)}
                {earlier.length > 0 && (
                    <details className="mt-2 text-sm text-muted-foreground">
                        <summary>Earlier versions of these limits ({earlier.length})</summary>
                        {earlier.map(row)}
                    </details>
                )}
            </CardContent>

            <Dialog open={!!acting} onOpenChange={(o) => { if (!o) close(); }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {acting?.kind === "reset" ? "Reset life" : "Extend the limit"}: {acting?.t.definition_name}
                        </DialogTitle>
                        <DialogDescription>
                            {acting?.kind === "reset"
                                ? "Puts what it has used back to zero — after refurbishment or overhaul. Say what was done."
                                : "Raises the hard limit for this item only. Say why it's safe to run longer."}
                        </DialogDescription>
                    </DialogHeader>
                    {acting?.kind === "extend" && (
                        <div className="space-y-1">
                            <Label htmlFor="life-hard">New hard limit</Label>
                            <Input id="life-hard" type="number" min={0} step="any" value={hard}
                                onChange={(e) => setHard(e.target.value)} />
                        </div>
                    )}
                    <div className="space-y-1">
                        <Label htmlFor="life-reason">Reason</Label>
                        <Textarea id="life-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={close}>Cancel</Button>
                        <Button onClick={() => act.mutate()}
                            disabled={!reason.trim() || (acting?.kind === "extend" && !hard) || act.isPending}>
                            {acting?.kind === "reset" ? "Reset" : "Extend"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
