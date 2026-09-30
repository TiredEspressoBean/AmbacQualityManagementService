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
    GAUGE_UNAVAILABLE: "Gauge unavailable",
};

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
