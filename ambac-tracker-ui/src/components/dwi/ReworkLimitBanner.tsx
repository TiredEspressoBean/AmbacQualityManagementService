/**
 * Rework-limit / escalation banner (4b).
 *
 * Surfaces when the part's current step carries a visit cap (`max_visits`) —
 * i.e. it's a rework loop with engine-driven escalation. Shows how many
 * attempts the part has used vs the cap, how many remain, and the step it
 * escalates to (e.g. a scrap decision) once the cap is exceeded. When the cap
 * is reached, it warns that the next failure escalates automatically — the
 * escalation is engine-driven (`_check_cycle_limit`), not a manual scrap call.
 *
 * Renders nothing for steps without a cap (the common case).
 */
import { RotateCcw, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useReworkStatus } from "@/hooks/parts";

export function ReworkLimitBanner({ partId }: { partId: string }) {
    const { data } = useReworkStatus(partId);

    // Only meaningful on a visit-capped (rework-loop) step.
    if (!data || data.max_visits == null) return null;

    const { current_visits, max_visits, remaining, at_limit, escalation_step_name } = data;

    return (
        <div
            className={
                "rounded-lg border p-3 " +
                (at_limit
                    ? "border-destructive/50 bg-destructive/10"
                    : "border-amber-500/40 bg-amber-50/40 dark:bg-amber-950/20")
            }
        >
            <div className="flex items-center gap-2">
                {at_limit ? (
                    <AlertTriangle className="h-4 w-4 text-destructive" />
                ) : (
                    <RotateCcw className="h-4 w-4 text-amber-600" />
                )}
                <span className="text-sm font-medium">
                    Rework attempt {current_visits} of {max_visits}
                </span>
                {data.total_rework_count > 0 && (
                    <Badge variant="secondary" className="text-[10px]">
                        {data.total_rework_count} total rework{data.total_rework_count === 1 ? "" : "s"}
                    </Badge>
                )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
                {at_limit ? (
                    <>
                        Visit cap reached — the next failure escalates automatically
                        {escalation_step_name ? (
                            <> to <span className="font-medium text-destructive">{escalation_step_name}</span></>
                        ) : null}
                        . Escalation is engine-driven, not a manual scrap decision.
                    </>
                ) : (
                    <>
                        {remaining} more attempt{remaining === 1 ? "" : "s"} before this part escalates
                        {escalation_step_name ? (
                            <> to <span className="font-medium">{escalation_step_name}</span></>
                        ) : null}
                        .
                    </>
                )}
            </p>
        </div>
    );
}
