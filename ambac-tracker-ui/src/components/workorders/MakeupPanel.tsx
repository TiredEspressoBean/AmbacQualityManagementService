/**
 * Make-up: replace scrapped parts so a work order still delivers its ordered good count
 * (services/mes/makeup). Shows the gap and, when there is one, the planner-confirmed
 * action that creates the replacement parts at the route's first step.
 *
 * Shared by the schedule's work-order dialog and the work order page. The page passes
 * `onlyWhenShort`, so it appears there only when there's something to make up.
 */
import { Button } from "@/components/ui/button";
import { useCreateMakeup, useMakeupStatus } from "@/hooks/useScheduling";
import { usePermissionSet } from "@/hooks/useMyPermissions";

export function MakeupPanel({ workOrderId, onlyWhenShort = false }: {
    workOrderId: string;
    onlyWhenShort?: boolean;
}) {
    const { data: makeup } = useMakeupStatus(workOrderId);
    const createMakeup = useCreateMakeup();
    // The create action falls back to the work order's add permission.
    const canCreate = usePermissionSet().has("add_workorder");

    if (!makeup) return null;
    if (onlyWhenShort && makeup.shortfall <= 0) return null;

    return (
        <div className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between">
                <span className="font-medium">Make-up</span>
                <span className="text-xs text-muted-foreground">
                    {makeup.good}/{makeup.target_good} good · {makeup.alive} alive · {makeup.scrapped} scrapped
                </span>
            </div>
            {makeup.shortfall > 0 ? (
                <div className="mt-2 flex items-center justify-between gap-2">
                    <span className="text-red-600 dark:text-red-400">
                        {makeup.shortfall} short of {makeup.target_good} good
                    </span>
                    {canCreate && (
                        <Button
                            size="sm" variant="outline"
                            onClick={() => createMakeup.mutate(workOrderId)}
                            disabled={createMakeup.isPending}
                        >
                            Create {makeup.shortfall} make-up part{makeup.shortfall === 1 ? "" : "s"}
                        </Button>
                    )}
                </div>
            ) : (
                <p className="mt-1 text-xs text-muted-foreground">
                    On track for its ordered good count.
                </p>
            )}
        </div>
    );
}
