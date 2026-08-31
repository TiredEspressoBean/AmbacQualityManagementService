// Edit a work order's schedule-relevant attributes from the Gantt (Phase 4):
// priority, release date, due date, and quantity (adds/cancels parts). Re-solve to apply.
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useWorkOrder,
  useUpdateWorkOrder,
  useSetWorkOrderQuantity,
  useHoldWorkOrder,
  useReleaseWorkOrder,
  useCancelWorkOrder,
  useMakeupStatus,
  useCreateMakeup,
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
  const { data: makeupData } = useMakeupStatus(workOrderId);
  const createMakeup = useCreateMakeup();
  const wo = data as any;
  const makeup = makeupData as any;
  const onHold = !!wo?.current_hold;

  const [priority, setPriority] = useState("");
  const [release, setRelease] = useState("");
  const [due, setDue] = useState("");
  const [quantity, setQuantity] = useState("");

  useEffect(() => {
    if (!wo) return;
    setPriority(wo.priority != null ? String(wo.priority) : "");
    setRelease(dstr(wo.expected_start));
    setDue(dstr(wo.expected_completion));
    setQuantity(wo.quantity != null ? String(wo.quantity) : "");
  }, [wo]);

  const save = () => {
    if (!workOrderId || !wo) return;
    const patch: Record<string, unknown> = {};
    if (priority.trim() !== "" && Number(priority) !== wo.priority) patch.priority = Number(priority);
    patch.expected_start = release || null;
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
              <Label className="text-xs">Release date</Label>
              <Input type="date" value={release} onChange={(e) => setRelease(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Due date</Label>
              <Input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
            </div>
          </div>
        )}

        {wo && makeup && (
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
                <Button
                  size="sm" variant="outline"
                  onClick={() => workOrderId && createMakeup.mutate(workOrderId)}
                  disabled={createMakeup.isPending}
                >
                  Create {makeup.shortfall} make-up part{makeup.shortfall === 1 ? "" : "s"}
                </Button>
              </div>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">
                On track for its ordered good count.
              </p>
            )}
          </div>
        )}

        {wo && (
          <div className="flex flex-wrap gap-2 border-t pt-3">
            {onHold ? (
              <Button
                variant="outline" size="sm"
                onClick={() => workOrderId && releaseHold.mutate(workOrderId)}
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
