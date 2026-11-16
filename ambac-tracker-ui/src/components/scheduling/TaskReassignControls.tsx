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
  /** Who's on it now, for when they aren't among the qualified on-shift crew. */
  operatorName?: string | null;
};

export function TaskReassignControls({ taskId, machineId, operatorId, operatorName }: Props) {
  const { data, isLoading } = useReassignOptions(taskId);
  const reassignMachine = useReassignMachine();
  const reassignOperator = useReassignOperator();

  const machines = useMemo(
    () => data?.machines ?? [],
    [data]
  );
  const operators = useMemo(
    () => data?.operators ?? [],
    [data]
  );

  return (
    // `grid-cols-2` is minmax(auto, 1fr): a column will not shrink below its
    // content's min-content width, so a long machine name pushes its trigger past the
    // column and over the neighbouring one. `min-w-0` on each cell (and on the
    // trigger) lets the track shrink; the value then truncates instead of overflowing.
    <div className="grid grid-cols-2 gap-3 rounded-md border p-3">
      <div className="col-span-2 text-xs font-medium text-muted-foreground">
        Reassign — applies now, re-solve to optimize
      </div>
      <div className="grid min-w-0 gap-1">
        <Label className="text-[11px]">Machine</Label>
        <Select
          value={machineId ?? ""}
          disabled={isLoading || reassignMachine.isPending}
          onValueChange={(v) => reassignMachine.mutate({ id: taskId, machine_id: v })}
        >
          <SelectTrigger className="h-8 w-full min-w-0 [&>span]:truncate">
            <SelectValue placeholder={isLoading ? "Loading…" : "Pick a machine"} />
          </SelectTrigger>
          <SelectContent>
            {machines.map((m) => (
              <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid min-w-0 gap-1">
        <Label className="text-[11px]">Operator</Label>
        <Select
          value={operatorId ?? UNASSIGNED}
          disabled={isLoading || reassignOperator.isPending}
          onValueChange={(v) =>
            // Number(): a Select value is always a string, but `User` is a
            // BigAutoField so the endpoint wants the integer pk.
            reassignOperator.mutate({ id: taskId, operator_id: v === UNASSIGNED ? null : Number(v) })
          }
        >
          <SelectTrigger className="h-8 w-full min-w-0 [&>span]:truncate">
            <SelectValue placeholder={isLoading ? "Loading…" : "Pick an operator"} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={UNASSIGNED}>— Unassigned —</SelectItem>
            {/* The person on it now (a running op's holder) when the list of qualified
                crew on shift doesn't include them — else the value matches no item and
                the picker reads blank. */}
            {operatorId && !operators.some((o) => String(o.id) === operatorId) && (
              <SelectItem value={operatorId}>{operatorName ?? "Current operator"} (on it now)</SelectItem>
            )}
            {operators.map((o) => (
              <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>
            ))}
            {!isLoading && operators.length === 0 && (
              // Not selectable: says why the list is empty (the step's or machine's
              // training), rather than offering an empty pick.
              <div className="px-2 py-1.5 text-xs text-muted-foreground">
                No operator on shift is qualified for this step on this machine.
              </div>
            )}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
