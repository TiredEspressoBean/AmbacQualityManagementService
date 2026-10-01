import { useState } from "react";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { HOLD_LABELS, SELF_CLEARING_HOLDS } from "@/components/receiving/lotStatus";
import { useConfirmWholeLotReject, useReleaseHold, useUpdateLotHeatNumber } from "@/hooks/useReceivingMutations";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import type { Schema } from "@/lib/api/types";

type Lot = Schema<"MaterialLot">;

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
    const reason = lot.hold_reason ?? "";
    const [heat, setHeat] = useState(lot.heat_number ?? "");
    const [releaseReason, setReleaseReason] = useState("");
    const [releasing, setReleasing] = useState(false);
    const release = useReleaseHold();
    const saveHeat = useUpdateLotHeatNumber();
    const perms = usePermissionSet();
    const canRelease = perms.has("approve_disposition");
    const canRejectWholeLot = perms.has("reject_whole_lot");
    const confirmWhole = useConfirmWholeLotReject();

    if (lot.status !== "QUARANTINE" || !reason) return null;
    const selfClearing = SELF_CLEARING_HOLDS.includes(reason);

    const errorOf = (err: unknown, fallback: string) =>
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

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
            {reason === "WHOLE_LOT_REJECT_REQUESTED" && canRejectWholeLot && (
                <Button size="sm" variant="destructive" disabled={confirmWhole.isPending}
                    onClick={() => confirmWhole.mutate({ id: String(lot.id) }, {
                        onSuccess: () => toast.success("Whole lot rejected · disposition updated"),
                        onError: (e) => toast.error(errorOf(e, "Could not reject the whole lot")),
                    })}>
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
                    Release hold…
                </Button>
            )}
            {canRelease && releasing && (
                <div className="space-y-2">
                    <Label htmlFor="hold-release">Why is this lot being released?</Label>
                    <Textarea id="hold-release" rows={2}
                        placeholder={reason === "SUPPLIER_UNQUALIFIED"
                            ? "e.g. Qualification renewal in progress; QA accepts this lot on its CoC and a 100% visual"
                            : "The decision, and what it rests on"}
                        value={releaseReason} onChange={(e) => setReleaseReason(e.target.value)} />
                    <div className="flex gap-2">
                        <Button size="sm" disabled={!releaseReason.trim() || release.isPending}
                            onClick={() => release.mutate({ id: String(lot.id), reason: releaseReason.trim() }, {
                                onSuccess: () => { toast.success("Hold released — the lot has moved on."); setReleasing(false); },
                                onError: (e) => toast.error(errorOf(e, "Could not release the hold")),
                            })}>
                            {release.isPending ? "Releasing…" : "Release hold"}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setReleasing(false)}>Cancel</Button>
                    </div>
                </div>
            )}
            {!canRelease && !selfClearing && (
                <p className="text-xs text-muted-foreground">
                    A quality manager can release this hold, or the lot can be rejected.
                </p>
            )}
        </div>
    );
}
