/** Why a work order is on hold: the reason, notes, who placed it, for how long, and
 *  when it's expected to clear — what a lead needs to decide whether to resume. */
import { PauseCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { HOLD_REASONS } from "@/pages/workorders/constants";

export type WorkOrderHold = {
    reason: string;
    placed_at?: string | null;
    placed_by_name?: string | null;
    notes?: string | null;
    hours_open?: number | null;
    expected_clear_at?: string | null;
};

export const holdReasonLabel = (reason: string) =>
    HOLD_REASONS.find((r) => r.value === reason)?.label ?? reason;

export function WorkOrderHoldBanner({ hold }: { hold: WorkOrderHold }) {
    return (
        <Card className="border-amber-500/50" role="status">
            <CardContent className="flex items-start gap-3 p-3">
                <PauseCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                <div className="flex-1 space-y-0.5 text-sm">
                    <div className="font-medium">On hold · {holdReasonLabel(hold.reason)}</div>
                    <div className="text-xs text-muted-foreground">
                        {hold.hours_open != null ? `${hold.hours_open}h open` : "Open"}
                        {hold.placed_by_name ? ` · placed by ${hold.placed_by_name}` : ""}
                        {hold.placed_at ? ` on ${new Date(hold.placed_at).toLocaleString()}` : ""}
                        {hold.expected_clear_at
                            ? ` · expected clear ${new Date(hold.expected_clear_at).toLocaleDateString()}`
                            : ""}
                    </div>
                    {hold.notes && <div className="text-xs text-muted-foreground">{hold.notes}</div>}
                </div>
            </CardContent>
        </Card>
    );
}

export type ClearedHold = WorkOrderHold & {
    id: string;
    cleared_at: string;
    cleared_by_name?: string | null;
    clear_notes?: string | null;
};

/** The order's cleared holds: why each stopped it, who released it, and what resolved it. */
export function WorkOrderHoldHistory({ holds }: { holds: readonly ClearedHold[] }) {
    if (holds.length === 0) return null;
    return (
        <details className="rounded-lg border px-3 py-2 text-sm">
            <summary className="cursor-pointer font-medium">Hold history ({holds.length})</summary>
            <ul className="mt-2 space-y-2">
                {holds.map((h) => (
                    <li key={h.id} className="border-t pt-2 first:border-t-0 first:pt-0">
                        <div>
                            <span className="font-medium">{holdReasonLabel(h.reason)}</span>
                            {h.notes ? <span className="text-muted-foreground"> — {h.notes}</span> : null}
                        </div>
                        <div className="text-xs text-muted-foreground">
                            Placed{h.placed_by_name ? ` by ${h.placed_by_name}` : ""}
                            {h.placed_at ? ` ${new Date(h.placed_at).toLocaleString()}` : ""}
                            {" · "}cleared{h.cleared_by_name ? ` by ${h.cleared_by_name}` : ""}
                            {` ${new Date(h.cleared_at).toLocaleString()}`}
                        </div>
                        <div className="text-xs">
                            {h.clear_notes ? <>Resolved: {h.clear_notes}</> : <span className="text-muted-foreground">No resolution note.</span>}
                        </div>
                    </li>
                ))}
            </ul>
        </details>
    );
}
