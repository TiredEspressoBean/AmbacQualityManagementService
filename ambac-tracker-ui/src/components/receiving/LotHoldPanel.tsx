import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { HOLD_LABELS, SELF_CLEARING_HOLDS, lotHolds } from "@/components/receiving/lotStatus";
import { useConfirmWholeLotReject, useReleaseHold, useUpdateLotHeatNumber } from "@/hooks/useReceivingMutations";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import type { Schema } from "@/lib/api/types";
import { apiErrorMessage } from "@/lib/api/describeApiError";

type Lot = Schema<"MaterialLot">;

/** The open disposition a whole-lot request opened — who asked, and why. */
const lotRequestOptions = (lotId: string) =>
    queryOptions({
        queryKey: ["dispositions", "lot-request", lotId] as const,
        queryFn: () => api.api_QuarantineDispositions_list({
            queries: { quality_reports__material_lot: lotId, ordering: "-created_at", limit: 5 },
        }),
        select: (d) => (d.results ?? []).find((r) => r.current_state !== "CLOSED") ?? null,
    });

/** The request in front of the decider: who asked, their reason, and where the
 *  inspection and its disposition are — so it isn't decided blind. */
function WholeLotRequestDetail({ lotId }: { lotId: string }) {
    const { data: req } = useQuery(lotRequestOptions(lotId));
    if (!req) return null;
    return (
        <div className="space-y-1 rounded border bg-background/60 p-2 text-sm">
            <div>
                <span className="text-muted-foreground">Requested by </span>
                <b>{req.assignee_name || "an inspector"}</b>
                {req.created_at ? <span className="text-muted-foreground"> · {new Date(req.created_at).toLocaleString()}</span> : null}
            </div>
            {req.description && <div className="italic">“{req.description}”</div>}
            <div className="flex gap-3 text-xs">
                <Link to="/production/receiving-inspection/$lotId" params={{ lotId }} className="underline underline-offset-2">
                    The inspection
                </Link>
                <Link to="/production/dispositions/$id/edit" params={{ id: String(req.id) }} className="underline underline-offset-2">
                    {req.disposition_number}
                </Link>
            </div>
        </div>
    );
}

/** What clears each self-clearing hold, said plainly. */
const HOW_TO_CLEAR: Record<string, string> = {
    AWAITING_COC: "Upload the certificate of conformance below. The lot moves on as soon as it's attached.",
    AWAITING_HEAT_NUMBER: "Enter the heat number from the mill certificate. The lot moves on as soon as it's saved.",
    SHELF_LIFE_EXPIRED: "Extend the shelf life after a re-test, or reject the lot.",
};

/** A hold that is a request for someone else's decision, said plainly. */
const REQUEST_TEXT: Record<string, string> = {
    WHOLE_LOT_REJECT_REQUESTED:
        "An inspector asked to reject the whole lot back to the vendor. Confirm it, or release " +
        "the hold to send the lot back to inspection for a partial reject.",
};

/**
 * A lot held at receiving: why, and what gets it moving. A paperwork hold clears itself
 * once the missing CoC or heat number is supplied. A decision hold — an unqualified
 * supplier, an unapproved part — needs QA to release it with a reason on record (or to
 * reject the lot). Either way the lot then routes on as if it had just arrived.
 */
export function LotHoldPanel({ lot }: { lot: Lot }) {
    const holds = lotHolds(lot);
    if (lot.status !== "QUARANTINE" || holds.length === 0) return null;
    // One card per hold: each is cleared on its own, and the lot moves on when the last goes.
    return (
        <div className="space-y-2">
            {holds.length > 1 && (
                <p className="text-sm font-medium text-amber-700">Held for {holds.length} reasons — each clears on its own.</p>
            )}
            {holds.map((code) => <HoldCard key={code} lot={lot} reason={code} several={holds.length > 1} />)}
        </div>
    );
}

function HoldCard({ lot, reason, several }: { lot: Lot; reason: string; several: boolean }) {
    const [heat, setHeat] = useState(lot.heat_number ?? "");
    const [releaseReason, setReleaseReason] = useState("");
    const [releasing, setReleasing] = useState(false);
    const release = useReleaseHold();
    const saveHeat = useUpdateLotHeatNumber();
    const perms = usePermissionSet();
    const canRelease = perms.has("approve_disposition");
    const canRejectWholeLot = perms.has("reject_whole_lot");
    const confirmWhole = useConfirmWholeLotReject();

    const selfClearing = SELF_CLEARING_HOLDS.includes(reason);

    const errorOf = (err: unknown, fallback: string) =>
        apiErrorMessage(err) ?? fallback;

    return (
        <div className="space-y-3 rounded-md border border-amber-300 bg-amber-50/50 p-3 text-sm dark:bg-amber-950/20">
            <div className="flex items-center gap-2 font-medium">
                <ShieldAlert className="h-4 w-4 text-amber-600" />
                Held at receiving: {HOLD_LABELS[reason] ?? reason}
            </div>
            {selfClearing && HOW_TO_CLEAR[reason] && (
                <p className="text-muted-foreground">{HOW_TO_CLEAR[reason]}</p>
            )}
            {REQUEST_TEXT[reason] && <p className="text-muted-foreground">{REQUEST_TEXT[reason]}</p>}
            {reason === "WHOLE_LOT_REJECT_REQUESTED" && <WholeLotRequestDetail lotId={String(lot.id)} />}
            {reason === "WHOLE_LOT_REJECT_REQUESTED" && canRejectWholeLot && (
                <Button size="sm" variant="destructive" disabled={confirmWhole.isPending}
                    onClick={async () => {
                        try {
                            await confirmWhole.mutateAsync({ id: String(lot.id) });
                            toast.success("Whole lot rejected · disposition updated");
                        } catch (e) {
                            toast.error(errorOf(e, "Could not reject the whole lot"));
                        }
                    }}>
                    {confirmWhole.isPending ? "Rejecting…" : "Confirm: reject whole lot"}
                </Button>
            )}

            {reason === "AWAITING_HEAT_NUMBER" && (
                <div className="flex items-end gap-2">
                    <div className="space-y-1">
                        <Label htmlFor="hold-heat">Heat number</Label>
                        <Input id="hold-heat" className="w-48 font-mono" value={heat}
                            onChange={(e) => setHeat(e.target.value)} />
                    </div>
                    <Button size="sm" disabled={!heat.trim() || saveHeat.isPending}
                        onClick={() => saveHeat.mutate({ id: String(lot.id), heat_number: heat.trim() }, {
                            onSuccess: () => toast.success("Heat number saved — the hold has cleared."),
                            onError: (e) => toast.error(errorOf(e, "Could not save the heat number")),
                        })}>
                        {saveHeat.isPending ? "Saving…" : "Save"}
                    </Button>
                </div>
            )}

            {/* Any hold can be released by QA — a paperwork hold too, when the paperwork
                is genuinely waived for this lot. The reason is kept on record. */}
            {canRelease && !releasing && (
                <Button size="sm" variant="outline" onClick={() => setReleasing(true)}>
                    {/* Here release means the opposite of everywhere else: it turns the
                        request down and sends the lot back for a partial reject. */}
                    {reason === "WHOLE_LOT_REJECT_REQUESTED" ? "Decline request…" : several ? "Release this hold…" : "Release hold…"}
                </Button>
            )}
            {canRelease && releasing && (
                <div className="space-y-2">
                    <Label htmlFor="hold-release">
                        {reason === "WHOLE_LOT_REJECT_REQUESTED"
                            ? "Why is the whole-lot reject being declined?"
                            : "Why is this lot being released?"}
                    </Label>
                    <Textarea id="hold-release" rows={2}
                        placeholder={reason === "SUPPLIER_UNQUALIFIED"
                            ? "e.g. Qualification renewal in progress; QA accepts this lot on its CoC and a 100% visual"
                            : "The decision, and what it rests on"}
                        value={releaseReason} onChange={(e) => setReleaseReason(e.target.value)} />
                    <div className="flex gap-2">
                        <Button size="sm" disabled={!releaseReason.trim() || release.isPending}
                            onClick={async () => {
                                // mutateAsync, not mutate(…, {onSuccess}): releasing the last hold
                                // unmounts this panel, and a mutate() callback doesn't fire after
                                // unmount — so the toast never showed.
                                try {
                                    await release.mutateAsync({ id: String(lot.id), reason: releaseReason.trim(), code: reason });
                                    toast.success(reason === "WHOLE_LOT_REJECT_REQUESTED"
                                        ? "Request declined — the lot is back in inspection."
                                        : several ? "Hold released — the lot's other holds still stand."
                                            : "Hold released — the lot has moved on.");
                                    setReleasing(false);
                                } catch (e) {
                                    toast.error(errorOf(e, "Could not release the hold"));
                                }
                            }}>
                            {release.isPending ? "Saving…"
                                : reason === "WHOLE_LOT_REJECT_REQUESTED" ? "Decline — back to inspection" : "Release hold"}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setReleasing(false)}>Cancel</Button>
                    </div>
                </div>
            )}
            {!canRelease && !selfClearing && (
                <p className="text-xs text-muted-foreground">
                    A quality manager can release this hold. Once released the lot is
                    inspected, and it can be rejected from the inspection.
                </p>
            )}
        </div>
    );
}
