// Scheduling settings dialog — edits the tenant's OptimizationConfig (solver knobs)
// from the /production/scheduling Gantt page. GET seeds the form; Save PATCHes.
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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useOptimizationConfig,
  useUpdateOptimizationConfig,
} from "@/hooks/useScheduling";
import { ShiftsSettingsTab } from "./ShiftsSettingsTab";

type Props = { open: boolean; onOpenChange: (o: boolean) => void };

// Editable fields, grouped. Numeric fields are coerced to Number on save; decimal
// (money/percent) fields are sent as strings (DRF DecimalField accepts strings).
type FieldSpec = { key: string; label: string; hint?: string; kind: "int" | "float" | "decimal" };

const SOLVER: FieldSpec[] = [
  { key: "solver_time_limit_seconds", label: "Solve time limit (seconds)", kind: "int",
    hint: "CP-SAT wall-clock cap per solve; best-so-far returned when it elapses." },
  { key: "relative_gap_limit", label: "Relative gap limit", kind: "float",
    hint: "Stop when within this optimality gap (0.02 = 2%)." },
];
const FENCES: FieldSpec[] = [
  { key: "frozen_zone_days", label: "Frozen zone (days)", kind: "int",
    hint: "Near-term window whose tasks the solver keeps fixed." },
  { key: "slushy_zone_days", label: "Slushy zone (days)", kind: "int",
    hint: "Window after frozen where moves are discouraged." },
];
const FLOW: FieldSpec[] = [
  { key: "staging_buffer_minutes", label: "Staging buffer (min)", kind: "int",
    hint: "Delay between a component WO finishing and its parent assembly starting." },
  { key: "job_change_minutes", label: "Job-change setup (min)", kind: "int",
    hint: "Setup charged when a resource switches work order on the same op." },
  { key: "default_move_minutes", label: "Move / queue time (min)", kind: "int",
    hint: "Transport + queue gap between consecutive operations of a route (0 = none)." },
];
const COSTS: FieldSpec[] = [
  { key: "shop_rate_per_hour", label: "Shop rate / hour", kind: "decimal" },
  { key: "overtime_multiplier", label: "Overtime multiplier", kind: "decimal" },
  { key: "pfd_allowance_pct", label: "PFD allowance (%)", kind: "decimal" },
  { key: "late_penalty_urgent", label: "Late penalty — urgent", kind: "decimal" },
  { key: "late_penalty_high", label: "Late penalty — high", kind: "decimal" },
  { key: "late_penalty_normal", label: "Late penalty — normal", kind: "decimal" },
  { key: "late_penalty_low", label: "Late penalty — low", kind: "decimal" },
];

const LABOR_MODELS = [
  { value: "pool", label: "Pool (cap at qualified crew on shift)" },
  { value: "off", label: "Off (no crew constraint)" },
  { value: "named", label: "Named (assign a specific operator)" },
];

const AUTO_RESOLVE_MODES = [
  { value: "off", label: "Off (flag stale only — planner re-solves by hand)" },
  { value: "live", label: "Live (auto re-solve & supersede the schedule)" },
];
const AUTO_INT: FieldSpec[] = [
  { key: "auto_resolve_min_interval_minutes", label: "Min re-solve interval (min)", kind: "int",
    hint: "Anti-churn floor: don't auto re-solve sooner than this after the last solve." },
];

export function SchedulingSettingsDialog({ open, onOpenChange }: Props) {
  const { data, isLoading } = useOptimizationConfig();
  const update = useUpdateOptimizationConfig();
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [tab, setTab] = useState("solver");

  // Seed the form whenever the dialog opens with fresh config.
  useEffect(() => {
    if (open && data) setForm({ ...(data as Record<string, unknown>) });
  }, [open, data]);

  const set = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const numField = (f: FieldSpec) => (
    <div key={f.key} className="grid gap-1">
      <Label htmlFor={f.key} className="text-xs">{f.label}</Label>
      <Input
        id={f.key}
        type={f.kind === "decimal" ? "text" : "number"}
        inputMode="decimal"
        step={f.kind === "float" ? "0.01" : f.kind === "int" ? "1" : "any"}
        value={(form[f.key] as string | number | undefined) ?? ""}
        onChange={(e) => set(f.key, e.target.value)}
        title={f.hint}
      />
      {f.hint && <p className="text-[11px] text-muted-foreground">{f.hint}</p>}
    </div>
  );

  const onSave = () => {
    // Coerce numeric fields; leave decimals as strings; booleans/select pass through.
    const payload: Record<string, unknown> = {};
    for (const f of [...SOLVER, ...FENCES, ...FLOW, ...AUTO_INT]) {
      const raw = form[f.key];
      if (raw === "" || raw == null) continue;
      payload[f.key] = f.kind === "decimal" ? String(raw) : Number(raw);
    }
    for (const f of COSTS) {
      const raw = form[f.key];
      if (raw === "" || raw == null) continue;
      payload[f.key] = String(raw);
    }
    payload.match_operators = !!form.match_operators;
    payload.default_lockstep_batch = !!form.default_lockstep_batch;
    if (form.default_labor_model) payload.default_labor_model = form.default_labor_model;
    if (form.auto_resolve) payload.auto_resolve = form.auto_resolve;
    update.mutate(payload, { onSuccess: () => onOpenChange(false) });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Scheduling settings</DialogTitle>
          <DialogDescription>
            Solver knobs for this tenant. Applied on the next Solve / What-if / Dispatch.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="mb-3">
            <TabsTrigger value="solver">Solver</TabsTrigger>
            <TabsTrigger value="shifts">Work hours</TabsTrigger>
          </TabsList>

          <TabsContent value="solver" className="mt-0">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="grid gap-5">
            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Solver</h4>
              <div className="grid grid-cols-2 gap-3">{SOLVER.map(numField)}</div>
            </section>

            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Time fences</h4>
              <div className="grid grid-cols-2 gap-3">{FENCES.map(numField)}</div>
            </section>

            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Labor</h4>
              <div className="grid gap-1">
                <Label className="text-xs">Default labor model</Label>
                <Select
                  value={(form.default_labor_model as string) ?? "pool"}
                  onValueChange={(v) => set("default_labor_model", v)}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {LABOR_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <Label className="text-sm">Match operators (two-phase solve)</Label>
                  <p className="text-[11px] text-muted-foreground">
                    Solve machines, then assign a specific operator to every attended op.
                  </p>
                </div>
                <Switch
                  checked={!!form.match_operators}
                  onCheckedChange={(v) => set("match_operators", v)}
                />
              </div>
              <div className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <Label className="text-sm">Default lock-step batch</Label>
                  <p className="text-[11px] text-muted-foreground">
                    Default lot-cohesion intent for WOs that don't set their own.
                  </p>
                </div>
                <Switch
                  checked={!!form.default_lockstep_batch}
                  onCheckedChange={(v) => set("default_lockstep_batch", v)}
                />
              </div>
            </section>

            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Automatic rescheduling</h4>
              <div className="grid gap-1">
                <Label className="text-xs">When the plan drifts stale</Label>
                <Select
                  value={(form.auto_resolve as string) ?? "off"}
                  onValueChange={(v) => set("auto_resolve", v)}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {AUTO_RESOLVE_MODES.map((m) => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-muted-foreground">
                  Live re-solves in the background when a quality hold, new demand, or
                  lost capacity drifts the plan. The frozen zone + pins keep committed
                  near-term work in place.
                </p>
              </div>
              {form.auto_resolve === "live" && (
                <div className="grid grid-cols-2 gap-3">{AUTO_INT.map(numField)}</div>
              )}
            </section>

            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Convergence & setup</h4>
              <div className="grid grid-cols-2 gap-3">{FLOW.map(numField)}</div>
            </section>

            <section className="grid gap-3">
              <h4 className="text-sm font-medium">Costs & penalties</h4>
              <div className="grid grid-cols-2 gap-3">{COSTS.map(numField)}</div>
            </section>
          </div>
        )}
          </TabsContent>

          <TabsContent value="shifts" className="mt-0">
            <ShiftsSettingsTab />
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tab === "shifts" ? "Close" : "Cancel"}
          </Button>
          {tab === "solver" && (
            <Button onClick={onSave} disabled={update.isPending || isLoading}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
