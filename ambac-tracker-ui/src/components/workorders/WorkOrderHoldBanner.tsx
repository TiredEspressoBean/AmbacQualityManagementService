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
