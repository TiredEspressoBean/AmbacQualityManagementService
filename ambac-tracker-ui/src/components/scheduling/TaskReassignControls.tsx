// Reassign a scheduled task's machine / operator from the detail dialog (Phase 3).
// Applies immediately (+ pins for machine); the solver reconciles on the next Solve.
import { useMemo } from "react";
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
  useReassignMachine,
  useReassignOperator,
} from "@/hooks/useScheduling";

const UNASSIGNED = "__none__";

type Props = {
  taskId: string;
  machineId: string | null;
  operatorId: string | null;
};

export function TaskReassignControls({ taskId, machineId, operatorId }: Props) {
  const { data, isLoading } = useReassignOptions(taskId);
  const reassignMachine = useReassignMachine();
  const reassignOperator = useReassignOperator();

  const machines = useMemo(
    () => ((data as any)?.machines ?? []) as { id: string; name: string }[],
    [data]
  );
  const operators = useMemo(
    () => ((data as any)?.operators ?? []) as { id: string; name: string }[],
    [data]
  );

  return (
    <div className="grid grid-cols-2 gap-3 rounded-md border p-3">
      <div className="col-span-2 text-xs font-medium text-muted-foreground">
        Reassign — applies now, re-solve to optimize
      </div>
      <div className="grid gap-1">
        <Label className="text-[11px]">Machine</Label>
        <Select
          value={machineId ?? ""}
          disabled={isLoading || reassignMachine.isPending}
          onValueChange={(v) => reassignMachine.mutate({ id: taskId, machine_id: v })}
        >
          <SelectTrigger className="h-8">
            <SelectValue placeholder={isLoading ? "Loading…" : "Pick a machine"} />
          </SelectTrigger>
          <SelectContent>
            {machines.map((m) => (
              <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-1">
        <Label className="text-[11px]">Operator</Label>
        <Select
          value={operatorId ?? UNASSIGNED}
          disabled={isLoading || reassignOperator.isPending}
          onValueChange={(v) =>
            reassignOperator.mutate({ id: taskId, operator_id: v === UNASSIGNED ? null : v })
          }
        >
          <SelectTrigger className="h-8">
            <SelectValue placeholder={isLoading ? "Loading…" : "Pick an operator"} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={UNASSIGNED}>— Unassigned —</SelectItem>
            {operators.map((o) => (
              <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
