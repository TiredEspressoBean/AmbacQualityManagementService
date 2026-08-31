// "Add work" — create a work order + its parts from the Gantt, so a scheduler can
// plan new demand, not just reshuffle existing bars. Schedules on the next Solve.
import { useMemo, useState } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProcesses, usePlanWorkOrder } from "@/hooks/useScheduling";

type Props = { open: boolean; onOpenChange: (o: boolean) => void };

export function NewWorkOrderDialog({ open, onOpenChange }: Props) {
  const { data: procData, isLoading } = useProcesses();
  const plan = usePlanWorkOrder();

  const processes = useMemo(() => {
    const list = ((procData as any)?.results ?? procData ?? []) as any[];
    return Array.isArray(list) ? list : [];
  }, [procData]);

  const [processId, setProcessId] = useState("");
  const [quantity, setQuantity] = useState("10");
  const [priority, setPriority] = useState("");
  const [erpId, setErpId] = useState("");
  const [due, setDue] = useState("");
  const [release, setRelease] = useState("");

  const reset = () => {
    setProcessId(""); setQuantity("10"); setPriority(""); setErpId(""); setDue(""); setRelease("");
  };

  const qtyNum = Number(quantity);
  const canSubmit = !!processId && Number.isFinite(qtyNum) && qtyNum >= 1;

  const submit = () => {
    const body: Record<string, unknown> = { process: processId, quantity: qtyNum };
    if (erpId.trim()) body.erp_id = erpId.trim();
    if (priority.trim() !== "") body.priority = Number(priority);
    if (due) body.expected_completion = due;
    if (release) body.expected_start = release;
    plan.mutate(body, {
      onSuccess: () => { reset(); onOpenChange(false); },
    });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New work order</DialogTitle>
          <DialogDescription>
            Creates the work order and its parts at the process's first step. It
            schedules on the next Solve.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid gap-1">
            <Label className="text-xs">Process</Label>
            <Select value={processId} onValueChange={setProcessId} disabled={isLoading}>
              <SelectTrigger>
                <SelectValue placeholder={isLoading ? "Loading…" : "Pick a process"} />
              </SelectTrigger>
              <SelectContent>
                {processes.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}{p.part_type_name ? ` · ${p.part_type_name}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1">
              <Label className="text-xs">Quantity</Label>
              <Input type="number" min="1" value={quantity}
                onChange={(e) => setQuantity(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs" title="Lower = higher priority">Priority (optional)</Label>
              <Input type="number" value={priority} placeholder="default"
                onChange={(e) => setPriority(e.target.value)} />
            </div>
          </div>

          <div className="grid gap-1">
            <Label className="text-xs">Work order ID (optional)</Label>
            <Input value={erpId} placeholder="auto-generated"
              onChange={(e) => setErpId(e.target.value)} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1">
              <Label className="text-xs">Release date (optional)</Label>
              <Input type="date" value={release} onChange={(e) => setRelease(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Due date (optional)</Label>
              <Input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={!canSubmit || plan.isPending}>
            {plan.isPending ? "Creating…" : "Create work order"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
