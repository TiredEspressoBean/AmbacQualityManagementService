import { Badge } from "@/components/ui/badge";
import type { Schema } from "@/lib/api/types";

type Lot = Schema<"MaterialLot">;

// System-set MaterialLot.hold_reason codes → operator-facing labels (mirrors the
// vocabulary in services/qms/receiving_inspection.py). Shared across every lot
// surface so a held lot is never silently unlabeled.
export const HOLD_LABELS: Record<string, string> = {
    SUPPLIER_UNQUALIFIED: "Unqualified supplier",
    PART_UNAPPROVED: "Unapproved part",
    SHELF_LIFE_EXPIRED: "Shelf life expired",
    AWAITING_COC: "Awaiting CoC",
    AWAITING_HEAT_NUMBER: "Awaiting heat number",
    WHOLE_LOT_REJECT_REQUESTED: "Whole-lot reject requested",
    GAUGE_UNAVAILABLE: "Gauge unavailable",
};

// Holds that clear themselves once the missing thing is supplied (mirrors
// SELF_CLEARING_HOLDS). The rest are decisions a person releases, with a reason.
export const SELF_CLEARING_HOLDS = ["AWAITING_COC", "AWAITING_HEAT_NUMBER", "SHELF_LIFE_EXPIRED"];

export type SourceType = "MANUFACTURER" | "AUTHORIZED_DISTRIBUTOR" | "INDEPENDENT_DISTRIBUTOR";
export const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string }[] = [
    { value: "MANUFACTURER", label: "Manufacturer" },
    { value: "AUTHORIZED_DISTRIBUTOR", label: "Authorized distributor" },
    { value: "INDEPENDENT_DISTRIBUTOR", label: "Independent distributor" },
];

// A lot an operator can re-qualify: held for shelf life, or flagged EXPIRED.
export const canExtend = (l: Lot) =>
    l.hold_reason === "SHELF_LIFE_EXPIRED" || l.shelf_life_status === "EXPIRED";

/**
 * Hold-reason + shelf-life "nearing expiry" chips for a lot (NOT the status badge
 * itself, which each surface renders in its own style). Keeps the held/expiry
 * signal identical across the receiving queue, the Materials hub, and lot detail.
 */
export function LotHoldBadges({ lot }: { lot: Lot }) {
    const holdLabel = HOLD_LABELS[lot.hold_reason ?? ""];
    return (
        <>
            {holdLabel && (
                <Badge variant="outline" className="border-amber-400 text-amber-700">{holdLabel}</Badge>
            )}
            {lot.shelf_life_status === "WARNING" && lot.hold_reason !== "SHELF_LIFE_EXPIRED" && (
                <Badge variant="outline" className="border-amber-400 text-amber-700">Nearing expiry</Badge>
            )}
        </>
    );
}
