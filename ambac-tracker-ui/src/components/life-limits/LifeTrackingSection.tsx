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
import { ApprovalSignaturePanel } from "@/components/approval/ApprovalSignaturePanel";

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
    // Reset is life-limit authority; asking for an extension is open to staff — it's
    // decided by someone else with that authority (an approval request).
    const canReset = has("change_lifelimitdefinition");
    const canAskExtension = has("add_lifetracking");
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
                await api.api_LifeTracking_request_extension_create(
                    { hard_limit: hard, reason }, { params: { id }, headers });
            }
        },
        onSuccess: () => {
            toast.success(acting?.kind === "reset" ? "Life reset" : "Extension requested — waiting for approval");
            void qc.invalidateQueries(trackingsOptions(contentType, objectId));
            close();
        },
        onError: (e: unknown) => toast.error(apiErrorMessage(e) ?? "That didn't go through"),
    });

    if (rows.length === 0) return null;

    const lastReset = (t: Tracking) => {
        const h = (Array.isArray(t.reset_history) ? t.reset_history : []) as
            { at?: string; by?: string; reason?: string }[];
        return h.length ? h[h.length - 1] : null;
    };

    const row = (t: Tracking) => (
        <div key={String(t.id)} className="border-b py-2 last:border-b-0">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <div className="min-w-40 font-medium">
                {t.definition_name}
                {t.item_label && <span className="ml-1 text-xs font-normal text-muted-foreground"> ({t.item_label})</span>}
            </div>
            <div className="text-sm">
                {n(t.current_value)} used · soft {n(t.effective_soft_limit)} · hard {n(t.effective_hard_limit)}
                {t.definition_unit ? ` ${t.definition_unit.toLowerCase()}` : ""}
            </div>
            <Badge variant={STATUS_VARIANT[t.status] ?? "outline"}>{t.status}</Badge>
            {t.definition_is_current && (canReset || canAskExtension) && (
                <div className="ml-auto flex gap-2">
                    {canReset && (
                        <Button size="sm" variant="outline" onClick={() => setActing({ t, kind: "reset" })}>
                            Reset
                        </Button>
                    )}
                    {canAskExtension && !t.pending_extension && (
                        <Button size="sm" variant="outline" onClick={() => {
                            setHard("");
                            setActing({ t, kind: "extend" });
                        }}>
                            Extend
                        </Button>
                    )}
                </div>
            )}
        </div>
            {/* What was done to it, and by whom: the record behind its numbers. */}
            {(() => {
                const r = lastReset(t);
                return r ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                        Last reset {r.at ? new Date(r.at).toLocaleDateString() : ""}
                        {r.by ? ` by ${r.by}` : ""}{r.reason ? ` — ${r.reason}` : ""}
                    </p>
                ) : null;
            })()}
            {t.pending_extension && (
                <>
                    <p className="mt-1 text-xs text-amber-700 dark:text-amber-400">
                        Extension to {n(t.pending_hard_limit)} requested ({t.pending_extension}) —
                        waiting for approval.
                    </p>
                    {/* Decided here: someone with life-limit authority other than the
                        requester signs it (the panel offers it only to them). */}
                    <div className="mt-2">
                        <ApprovalSignaturePanel
                            contentTypeModel="lifetracking"
                            objectId={String(t.id)}
                            contentTitle={`${t.definition_name}: raise to ${n(t.pending_hard_limit)}`}
                            contentKind="Life limit extension"
                            title="Extension approval"
                            description="Approve to raise this item's hard limit; reject to leave it as it is."
                            onDecided={() => { void qc.invalidateQueries(trackingsOptions(contentType, objectId)); }}
                        />
                    </div>
                </>
            )}
            {t.hard_limit_override != null && (
                <p className="mt-1 text-xs text-muted-foreground">
                    Extended to {n(t.hard_limit_override)}
                    {t.override_approved_by_name ? `, approved by ${t.override_approved_by_name}` : ""}
                    {t.override_reason ? ` — ${t.override_reason}` : ""}
                </p>
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
                            {acting?.kind === "reset" ? "Reset life" : "Request an extension"}: {acting?.t.definition_name}
                        </DialogTitle>
                        <DialogDescription>
                            {acting?.kind === "reset"
                                ? "Puts what it has used back to zero — after refurbishment or overhaul. Say what was done."
                                : `Asks for this item's hard limit to be raised (now ${n(acting?.t.effective_hard_limit)}). Someone with life-limit authority, other than you, approves it; the limit rises only then. Say why it's safe to run longer.`}
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
                            {acting?.kind === "reset" ? "Reset" : "Request extension"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Card>
    );
}
