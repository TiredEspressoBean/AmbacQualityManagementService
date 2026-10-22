// Edit a work order's schedule-relevant attributes from the Gantt (Phase 4):
// priority, release date, due date, and quantity (adds/cancels parts). Re-solve to apply.
import type { WorkOrderHold } from "@/components/workorders/WorkOrderHoldBanner";
import { ClearHoldDialog } from "@/components/workorders/ClearHoldDialog";
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { MakeupPanel } from "@/components/workorders/MakeupPanel";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useWorkOrder,
  useUpdateWorkOrder,
  useSetWorkOrderQuantity,
  useHoldWorkOrder,
  useReleaseWorkOrder,
  useCancelWorkOrder,
  useReleaseReadiness,
  useReleaseForScheduling,
  useUnreleaseForScheduling,
  useOptimizationConfig,
  type ReleaseCheck,
} from "@/hooks/useScheduling";

type Props = { workOrderId: string | null; onOpenChange: (o: boolean) => void };

const dstr = (v: unknown) => (typeof v === "string" ? v.slice(0, 10) : "");

export function EditWorkOrderDialog({ workOrderId, onOpenChange }: Props) {
  const { data, isLoading } = useWorkOrder(workOrderId);
  const update = useUpdateWorkOrder();
  const setQty = useSetWorkOrderQuantity();
  const hold = useHoldWorkOrder();
  const releaseHold = useReleaseWorkOrder();
  const cancel = useCancelWorkOrder();
  const { data: readiness } = useReleaseReadiness(workOrderId);
  const { data: config } = useOptimizationConfig();
  const release = useReleaseForScheduling();
  const unrelease = useUnreleaseForScheduling();
  const wo = data;
  const onHold = !!wo?.current_hold;
  const released = !!wo?.released_at;
  // Under "auto" the gate never filters, so releasing is bookkeeping the planner
  // doesn't need to see. Only surface the section where it changes the plan.
  const manualRelease = config?.release_mode === "manual";
  // Blockers the backend already refused once. Holding them here is what turns the
  // second click into an informed override rather than a repeat of the same request.
  const [blockers, setBlockers] = useState<ReleaseCheck[]>([]);
  const [overrideReason, setOverrideReason] = useState("");
  const [clearingHold, setClearingHold] = useState(false);

  const doRelease = () => {
    if (!workOrderId) return;
    release.mutate(
      { id: workOrderId, override_reason: overrideReason },
      {
        onSuccess: () => { setBlockers([]); setOverrideReason(""); },
        onError: (e: any) => {
          if (e?.response?.status === 409) setBlockers(e.response.data?.blockers ?? []);
        },
      }
    );
  };

  const [priority, setPriority] = useState("");
  // `expected_start` is the solver's earliest-start bound, NOT the release gate — with
  // a real Release action on this dialog now, calling it "release date" would read as
  // the same thing twice.
  const [earliestStart, setEarliestStart] = useState("");
  const [due, setDue] = useState("");
  const [quantity, setQuantity] = useState("");

  useEffect(() => {
    if (!wo) return;
    setPriority(wo.priority != null ? String(wo.priority) : "");
    setEarliestStart(dstr(wo.expected_start));
    setDue(dstr(wo.expected_completion));
    setQuantity(wo.quantity != null ? String(wo.quantity) : "");
  }, [wo]);

  const save = () => {
    if (!workOrderId || !wo) return;
    const patch: Record<string, unknown> = {};
    if (priority.trim() !== "" && Number(priority) !== wo.priority) patch.priority = Number(priority);
    patch.expected_start = earliestStart || null;
    patch.expected_completion = due || null;
    update.mutate({ id: workOrderId, ...patch });

    const q = Number(quantity);
    if (Number.isFinite(q) && q >= 0 && q !== wo.quantity) {
      setQty.mutate({ id: workOrderId, quantity: q });
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={workOrderId != null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit work order{wo?.ERP_id ? ` · ${wo.ERP_id}` : ""}</DialogTitle>
          <DialogDescription>
            Changes apply to the plan and take effect on the next Solve. Quantity changes
            add parts (increase) or cancel unstarted parts (decrease).
          </DialogDescription>
        </DialogHeader>

        {isLoading || !wo ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1">
              <Label className="text-xs" title="Lower = higher priority">Priority</Label>
              <Input type="number" value={priority} onChange={(e) => setPriority(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Quantity</Label>
              <Input type="number" min="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs" title="The solver won't start this work order before this date">
                Earliest start
              </Label>
              <Input type="date" value={earliestStart}
                     onChange={(e) => setEarliestStart(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Due date</Label>
              <Input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
            </div>
          </div>
        )}

        {wo && workOrderId && <MakeupPanel workOrderId={workOrderId} />}

        {wo && manualRelease && (
          <div className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">
                {released ? "Released for scheduling" : "Not released"}
              </span>
              {released ? (
                <Button
                  size="sm" variant="outline"
                  onClick={() => {
                    if (!workOrderId) return;
                    // Under manual release the next solve drops its remaining work from
                    // the plan; with parts already on the floor, say so first.
                    const started = wo.workorder_status === "IN_PROGRESS";
                    const msg = started
                      ? "Work has started on this order. Withdrawing the release takes its remaining work off the plan at the next solve — the parts on the floor stop being scheduled. Release it again to bring them back. Withdraw?"
                      : "Withdraw the release? The next solve takes this order off the plan until it is released again.";
                    if (window.confirm(msg)) unrelease.mutate(workOrderId);
                  }}
                  disabled={unrelease.isPending}
                >
                  Withdraw release
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={doRelease}
                  // Once refused, the same request without a reason is refused again —
                  // require the justification before re-offering the button.
                  disabled={
                    release.isPending ||
                    (blockers.length > 0 && overrideReason.trim() === "")
                  }
                >
                  {blockers.length ? "Release anyway" : "Release"}
                </Button>
              )}
            </div>

            {released && wo.release_override_reason && (
              <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                Released over a failing check: {wo.release_override_reason}
              </p>
            )}

            {!released && readiness && (
              <ul className="mt-2 space-y-1 text-xs">
                {readiness.blockers.map((b) => (
                  <li key={b.code} className="text-red-600 dark:text-red-400">
                    ✕ {b.detail}
                  </li>
                ))}
                {readiness.warnings.map((w) => (
                  <li key={w.code} className="text-amber-700 dark:text-amber-400">
                    ! {w.detail}
                  </li>
                ))}
                {readiness.ok && readiness.warnings.length === 0 && (
                  <li className="text-muted-foreground">Ready to release.</li>
                )}
              </ul>
            )}

            {/* The gate is advisory: a refused release re-offers with a reason box
                rather than a dead end, and the reason is stored on the work order. */}
            {!released && blockers.length > 0 && (
              <div className="mt-2 grid gap-1">
                <Label className="text-xs">Reason for releasing anyway</Label>
                <Input
                  value={overrideReason}
                  placeholder="e.g. routing lands Thursday"
                  onChange={(e) => setOverrideReason(e.target.value)}
                />
              </div>
            )}
          </div>
        )}

        <ClearHoldDialog
          open={clearingHold}
          onOpenChange={setClearingHold}
          hold={(wo?.current_hold as WorkOrderHold | null) ?? null}
          pending={releaseHold.isPending}
          onConfirm={(notes) => workOrderId && releaseHold.mutate(
            { id: workOrderId, notes }, { onSuccess: () => setClearingHold(false) })}
        />
        {wo && (
          <div className="flex flex-wrap gap-2 border-t pt-3">
            {onHold ? (
              <Button
                variant="outline" size="sm"
                onClick={() => setClearingHold(true)}
                disabled={releaseHold.isPending}
              >
                Release hold
              </Button>
            ) : (
              <Button
                variant="outline" size="sm"
                onClick={() => workOrderId && hold.mutate({ id: workOrderId, reason: "OTHER" })}
                disabled={hold.isPending}
              >
                Put on hold
              </Button>
            )}
            <Button
              variant="destructive" size="sm"
              onClick={() => {
                if (workOrderId && window.confirm("Cancel this work order? It drops from the schedule.")) {
                  cancel.mutate(workOrderId, { onSuccess: () => onOpenChange(false) });
                }
              }}
              disabled={cancel.isPending}
            >
              Cancel work order
            </Button>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
          <Button onClick={save} disabled={isLoading || !wo || update.isPending || setQty.isPending}>
            {update.isPending || setQty.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
