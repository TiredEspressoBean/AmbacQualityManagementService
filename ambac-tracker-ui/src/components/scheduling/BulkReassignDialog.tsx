// Bulk reassign machine / operator across a multi-selection of Gantt bars.
// Options (eligible machines / qualified operators) are fetched for the first selected
// task's step as a representative; the backend warns per-step on anything ineligible.
// Applies immediately (+ pins for machine); the solver reconciles on the next Solve.
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useReassignOptions,
  useBulkReassignMachine,
  useBulkReassignOperator,
} from "@/hooks/useScheduling";

const UNASSIGNED = "__none__";

type Props = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  taskIds: string[];
  repTaskId: string | null; // first selected task — options are fetched for its step
  onDone?: () => void;
};

export function BulkReassignDialog({ open, onOpenChange, taskIds, repTaskId, onDone }: Props) {
  const { data, isLoading } = useReassignOptions(open ? repTaskId : null);
  const bulkMachine = useBulkReassignMachine();
  const bulkOperator = useBulkReassignOperator();
  // "" = leave field as-is; only set fields are applied.
  const [machineId, setMachineId] = useState("");
  const [operatorId, setOperatorId] = useState("");

  useEffect(() => {
    if (open) {
      setMachineId("");
      setOperatorId("");
    }
  }, [open]);

  const machines = ((data as any)?.machines ?? []) as { id: string; name: string }[];
  const operators = ((data as any)?.operators ?? []) as { id: string; name: string }[];

  const apply = () => {
    if (machineId) bulkMachine.mutate({ task_ids: taskIds, machine_id: machineId });
    if (operatorId)
      bulkOperator.mutate({
        task_ids: taskIds,
        operator_id: operatorId === UNASSIGNED ? null : operatorId,
      });
    onOpenChange(false);
    onDone?.();
  };

  const busy = bulkMachine.isPending || bulkOperator.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reassign {taskIds.length} tasks</DialogTitle>
          <DialogDescription>
            Set a machine and/or operator for every selected task. Leave a field blank to
            keep it unchanged. Applies now (machine pins); re-solve to optimize.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid gap-1">
            <Label className="text-xs">Machine</Label>
            <Select value={machineId} onValueChange={setMachineId} disabled={isLoading}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder={isLoading ? "Loading…" : "— keep as-is —"} />
              </SelectTrigger>
              <SelectContent>
                {machines.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1">
            <Label className="text-xs">Operator</Label>
            <Select value={operatorId} onValueChange={setOperatorId} disabled={isLoading}>
              <SelectTrigger className="h-9">
                <SelectValue placeholder={isLoading ? "Loading…" : "— keep as-is —"} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNASSIGNED}>— Unassign (clear) —</SelectItem>
                {operators.map((o) => (
                  <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy || (!machineId && !operatorId)}>
            {busy ? "Applying…" : "Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
