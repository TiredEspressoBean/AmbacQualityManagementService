/** Scheduling calendar (/production/calendar).
 *
 * Authors the non-working time the solver honors:
 *  - Plant closures (PlantCalendarException) — dated, plant-wide (blocks machines
 *    AND operators): holidays, shutdowns, inventory days.
 *  - Labor blocks (LaborCalendarBlock) — operators only: PTO / sick / training /
 *    meetings / breaks, one-off or weekly, company-wide or per person.
 *
 * One-off items render on the kibo-ui month grid; click a day (or several) to seed
 * the Add dialog with that date range. Weekly blocks live in the side list. The
 * side lists manage/delete everything.
 */
import { useMemo, useState } from "react";
import { eachDayOfInterval, endOfDay, format, isSameDay, startOfDay } from "date-fns";
import { Trash2 } from "lucide-react";

import {
  CalendarBody,
  CalendarDate,
  CalendarDatePagination,
  CalendarDatePicker,
  CalendarHeader,
  CalendarItem,
  CalendarMonthPicker,
  CalendarProvider,
  CalendarYearPicker,
  useCalendarYear,
  type Feature,
} from "@/components/kibo-ui/calendar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  usePlantClosures, useLaborBlocks, useCreatePlantClosure, useDeletePlantClosure,
  useCreateLaborBlock, useDeleteLaborBlock, useOvertimeWindows, useCreateOvertime,
  useDeleteOvertime, type PlantClosure, type LaborBlock, type Overtime,
} from "@/hooks/useCalendar";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useShifts } from "@/hooks/useScheduling";

const KIND_COLOR: Record<string, string> = {
  // closures
  HOLIDAY: "#ef4444", SHUTDOWN: "#dc2626", INVENTORY: "#f97316",
  // labor blocks
  PTO: "#f59e0b", SICK: "#fb923c", TRAINING: "#8b5cf6",
  MEETING: "#3b82f6", BREAK: "#64748b", OTHER: "#9ca3af",
  // additive
  OVERTIME: "#22c55e",
};
const DOW = [
  { n: "1", label: "Mon" }, { n: "2", label: "Tue" }, { n: "3", label: "Wed" },
  { n: "4", label: "Thu" }, { n: "5", label: "Fri" }, { n: "6", label: "Sat" },
  { n: "0", label: "Sun" },
];
const dayKey = (d: Date) => format(d, "yyyy-MM-dd");

// Expand a dated [start, end] span into one Feature per covered calendar day, so a
// multi-day closure/absence shows on every day it spans (kibo-ui places a feature on
// its end day only).
function spanFeatures(id: string, name: string, kind: string, startISO: string, endISO: string): Feature[] {
  const start = new Date(startISO);
  const end = new Date(endISO);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return [];
  const color = KIND_COLOR[kind] ?? KIND_COLOR.OTHER;
  return eachDayOfInterval({ start: startOfDay(start), end: startOfDay(end) }).map((d, i) => ({
    id: `${id}-${i}`,
    name,
    startAt: d,
    endAt: d,
    status: { id: kind, name: kind, color },
  }));
}

type AddState = {
  open: boolean;
  type: "closure" | "labor" | "overtime";
  // closure
  closureName: string;
  closureKind: string;
  closureRecurrence: "ONCE" | "YEARLY";
  // labor
  who: string; // "" = whole company, else user id
  laborKind: string;
  recurrence: "ONCE" | "WEEKLY";
  days: Set<string>;
  windowStart: string;
  windowEnd: string;
  overtimeShift: string; // shift id the overtime runs
  reason: string;
};

const initialAdd = (): AddState => ({
  open: false, type: "closure", closureName: "", closureKind: "HOLIDAY",
  closureRecurrence: "ONCE",
  who: "", laborKind: "PTO", recurrence: "ONCE", days: new Set(),
  windowStart: "09:00", windowEnd: "09:30", overtimeShift: "", reason: "",
});

export function SchedulingCalendarPage() {
  const { data: closures = [] } = usePlantClosures();
  const { data: blocks = [] } = useLaborBlocks();
  const { data: overtimes = [] } = useOvertimeWindows();
  const { data: usersPage } = useRetrieveUsers({ limit: 200, user_type: "INTERNAL" } as never);
  const users = usersPage?.results ?? [];
  const { data: shiftsPage } = useShifts();
  const shifts = (shiftsPage as { results?: { id: string; name: string }[] } | undefined)?.results ?? [];

  const createClosure = useCreatePlantClosure();
  const delClosure = useDeletePlantClosure();
  const createBlock = useCreateLaborBlock();
  const delBlock = useDeleteLaborBlock();
  const createOvertime = useCreateOvertime();
  const delOvertime = useDeleteOvertime();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [add, setAdd] = useState<AddState>(initialAdd);
  const [viewedYear] = useCalendarYear();

  const selectedDates = useMemo(
    () => [...selected].map((k) => new Date(`${k}T00:00:00`)),
    [selected]
  );

  const userName = (id: number | null | undefined) => {
    if (id == null) return "Everyone";
    const u = users.find((x) => x.id === id);
    if (!u) return `User ${id}`;
    return u.full_name || u.username || `User ${id}`;
  };

  // One-off items → calendar features (closures + ONCE labor blocks).
  const features = useMemo<Feature[]>(() => {
    const out: Feature[] = [];
    for (const c of closures) {
      if (!c.is_active) continue;
      const name = c.name || "Closure";
      const kind = c.kind || "HOLIDAY";
      if (c.recurrence === "YEARLY") {
        // Recur the stored month/day span onto the viewed year (± 1 to cover month
        // views that spill across a year boundary), preserving duration.
        const dur = new Date(c.end_time as string).getTime() - new Date(c.start_time as string).getTime();
        for (const y of [viewedYear - 1, viewedYear, viewedYear + 1]) {
          const os = new Date(c.start_time as string);
          os.setFullYear(y);
          out.push(...spanFeatures(`${c.id}-${y}`, name, kind, os.toISOString(),
            new Date(os.getTime() + dur).toISOString()));
        }
      } else {
        out.push(...spanFeatures(String(c.id), name, kind, c.start_time as string, c.end_time as string));
      }
    }
    for (const b of blocks) {
      if (!b.is_active || b.recurrence !== "ONCE" || !b.start_time || !b.end_time) continue;
      const label = `${userName(b.user)}: ${b.kind}`;
      out.push(...spanFeatures(String(b.id), label, b.kind || "OTHER",
        b.start_time as string, b.end_time as string));
    }
    for (const o of overtimes) {
      if (!o.is_active || o.recurrence !== "ONCE" || !o.start_date || !o.end_date) continue;
      out.push(...spanFeatures(String(o.id), `Overtime: ${o.shift_name ?? ""}`.trim(),
        "OVERTIME", o.start_date as string, o.end_date as string));
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closures, blocks, overtimes, users, viewedYear]);

  const recurring = useMemo(
    () => blocks.filter((b) => b.recurrence === "WEEKLY"),
    [blocks]
  );

  const toggleDay = (d: Date) => {
    const k = dayKey(d);
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  };

  const openAdd = (type: AddState["type"]) => {
    setAdd({ ...initialAdd(), open: true, type });
  };

  const selectedRange = () => {
    const ds = [...selected].sort();
    if (!ds.length) return null;
    return {
      start_time: startOfDay(new Date(`${ds[0]}T00:00:00`)).toISOString(),
      end_time: endOfDay(new Date(`${ds[ds.length - 1]}T00:00:00`)).toISOString(),
    };
  };

  // Overtime stores plain dates (the shift supplies the hours).
  const selectedDateRange = () => {
    const ds = [...selected].sort();
    if (!ds.length) return null;
    return { start_date: ds[0], end_date: ds[ds.length - 1] };
  };

  const submit = () => {
    if (add.type === "closure") {
      const range = selectedRange();
      if (!range) return;
      createClosure.mutate(
        { name: add.closureName || "Closure", kind: add.closureKind,
          recurrence: add.closureRecurrence, ...range, is_active: true },
        { onSuccess: () => { setAdd(initialAdd()); setSelected(new Set()); } }
      );
      return;
    }
    const reset = () => { setAdd(initialAdd()); setSelected(new Set()); };

    if (add.type === "overtime") {
      if (!add.overtimeShift) return;
      const ot: Record<string, unknown> = {
        shift: Number(add.overtimeShift),
        recurrence: add.recurrence,
        reason: add.reason,
        is_active: true,
      };
      if (add.recurrence === "ONCE") {
        const dr = selectedDateRange();
        if (!dr) return;
        Object.assign(ot, dr);
      } else {
        ot.days_of_week = [...add.days].join(",");
      }
      createOvertime.mutate(ot, { onSuccess: reset });
      return;
    }

    // labor block
    const base: Record<string, unknown> = {
      user: add.who ? Number(add.who) : null,
      kind: add.laborKind,
      recurrence: add.recurrence,
      reason: add.reason,
      is_active: true,
    };
    if (add.recurrence === "ONCE") {
      const range = selectedRange();
      if (!range) return;
      Object.assign(base, range);
    } else {
      Object.assign(base, {
        days_of_week: [...add.days].join(","),
        window_start: add.windowStart,
        window_end: add.windowEnd,
      });
    }
    createBlock.mutate(base, { onSuccess: reset });
  };

  const recurrenceOk = add.recurrence === "ONCE" ? selected.size > 0 : add.days.size > 0;
  const canSubmit =
    add.type === "closure"
      ? selected.size > 0
      : add.type === "overtime"
        ? Boolean(add.overtimeShift) && recurrenceOk
        : recurrenceOk;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Scheduling calendar</h1>
          <p className="text-sm text-muted-foreground">
            Plant closures and who's out — the non-working time the scheduler plans around.
            Click one or more days, then add a closure or absence.
          </p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {[["HOLIDAY", "Closure"], ["PTO", "PTO"], ["SICK", "Sick"], ["TRAINING", "Training"],
          ["MEETING", "Meeting"], ["BREAK", "Break"], ["OVERTIME", "Overtime"]].map(([k, label]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: KIND_COLOR[k] }} />
            {label}
          </span>
        ))}
      </div>

      {/* Selection action bar */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 px-3 py-2">
        <span className="text-sm">
          {selected.size === 0
            ? "No days selected"
            : `${selected.size} day${selected.size === 1 ? "" : "s"} selected`}
        </span>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" disabled={selected.size === 0}
            onClick={() => openAdd("closure")}>Add closure</Button>
          <Button size="sm" variant="outline" disabled={selected.size === 0}
            onClick={() => openAdd("labor")}>Add absence / meeting</Button>
          <Button size="sm" variant="outline" disabled={selected.size === 0}
            onClick={() => openAdd("overtime")}>Add overtime</Button>
          <Button size="sm" variant="ghost" onClick={() => openAdd("labor")}
            title="Add a recurring block without picking days">Add recurring…</Button>
          {selected.size > 0 && (
            <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Calendar */}
        <div className="lg:col-span-2 rounded-lg border">
          <CalendarProvider startDay={1}>
            <CalendarDate>
              <CalendarDatePicker>
                <CalendarMonthPicker />
                <CalendarYearPicker end={new Date().getFullYear() + 2} start={new Date().getFullYear() - 1} />
              </CalendarDatePicker>
              <CalendarDatePagination />
            </CalendarDate>
            <CalendarHeader />
            <CalendarBody features={features} onDayClick={toggleDay} selectedDates={selectedDates}>
              {({ feature }) => <CalendarItem feature={feature} key={feature.id} />}
            </CalendarBody>
          </CalendarProvider>
        </div>

        {/* Management lists */}
        <div className="space-y-4">
          <ListCard title="Plant closures" empty="No closures.">
            {closures.filter((c) => c.is_active).map((c: PlantClosure) => (
              <Row key={c.id}
                label={c.name || "Closure"}
                sub={`${c.kind} · ${fmtDate(c.start_time)}${sameDay(c.start_time, c.end_time) ? "" : `–${fmtDate(c.end_time)}`}${c.recurrence === "YEARLY" ? " · yearly" : ""}`}
                color={KIND_COLOR[c.kind || "HOLIDAY"]}
                onDelete={() => delClosure.mutate(String(c.id))} />
            ))}
          </ListCard>

          <ListCard title="Recurring blocks" empty="No recurring blocks.">
            {recurring.map((b: LaborBlock) => (
              <Row key={b.id}
                label={`${userName(b.user)}: ${b.kind}`}
                sub={`Weekly ${weeklyDays(b.days_of_week)} · ${b.window_start ?? ""}–${b.window_end ?? ""}`}
                color={KIND_COLOR[b.kind || "OTHER"]}
                onDelete={() => delBlock.mutate(String(b.id))} />
            ))}
          </ListCard>

          <ListCard title="One-off absences" empty="No one-off absences.">
            {blocks.filter((b) => b.recurrence === "ONCE" && b.is_active).map((b: LaborBlock) => (
              <Row key={b.id}
                label={`${userName(b.user)}: ${b.kind}`}
                sub={`${fmtDate(b.start_time)}${sameDay(b.start_time, b.end_time) ? "" : `–${fmtDate(b.end_time)}`}`}
                color={KIND_COLOR[b.kind || "OTHER"]}
                onDelete={() => delBlock.mutate(String(b.id))} />
            ))}
          </ListCard>

          <ListCard title="Overtime / extra shifts" empty="No overtime.">
            {overtimes.filter((o) => o.is_active).map((o: Overtime) => (
              <Row key={o.id}
                label={`Overtime: ${o.shift_name ?? "shift"}`}
                sub={o.recurrence === "WEEKLY"
                  ? `Weekly ${weeklyDays(o.days_of_week)}`
                  : `${fmtDate(o.start_date)}${o.start_date === o.end_date ? "" : `–${fmtDate(o.end_date)}`}`}
                color={KIND_COLOR.OVERTIME}
                onDelete={() => delOvertime.mutate(String(o.id))} />
            ))}
          </ListCard>
        </div>
      </div>

      {/* Add dialog */}
      <Dialog open={add.open} onOpenChange={(o) => setAdd((a) => ({ ...a, open: o }))}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {add.type === "closure" ? "Add plant closure"
                : add.type === "overtime" ? "Add overtime / extra shift"
                  : "Add absence / meeting"}
            </DialogTitle>
            <DialogDescription>
              {add.type === "closure"
                ? "Closes the whole plant (machines and operators) for the selected day(s)."
                : add.type === "overtime"
                  ? "Adds working time for the whole shop — operators and attended machines. Lights-out machines already run 24/7; plant closures still win."
                  : "Operators only — machines keep running. One-off (selected days) or weekly."}
            </DialogDescription>
          </DialogHeader>

          {add.type === "closure" ? (
            <div className="grid gap-3">
              <Field label="Name">
                <Input value={add.closureName} placeholder="e.g. Christmas / Summer shutdown"
                  onChange={(e) => setAdd((a) => ({ ...a, closureName: e.target.value }))} />
              </Field>
              <Field label="Kind">
                <KindSelect value={add.closureKind} onChange={(v) => setAdd((a) => ({ ...a, closureKind: v }))}
                  options={[["HOLIDAY", "Holiday"], ["SHUTDOWN", "Plant shutdown"], ["INVENTORY", "Inventory / stock-take"], ["OTHER", "Other"]]} />
              </Field>
              <Field label="Repeats">
                <KindSelect value={add.closureRecurrence}
                  onChange={(v) => setAdd((a) => ({ ...a, closureRecurrence: v as "ONCE" | "YEARLY" }))}
                  options={[["ONCE", "One-off (this date only)"], ["YEARLY", "Every year (fixed-date holiday)"]]} />
              </Field>
              <SelectedDaysHint count={selected.size} />
            </div>
          ) : add.type === "overtime" ? (
            <div className="grid gap-3">
              <Field label="Which shift">
                {shifts.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground">
                    No shifts defined yet — add one under Scheduling settings → Work hours first.
                  </p>
                ) : (
                  <KindSelect value={add.overtimeShift}
                    onChange={(v) => setAdd((a) => ({ ...a, overtimeShift: v }))}
                    options={shifts.map((s) => [String(s.id), s.name] as [string, string])} />
                )}
              </Field>
              <Field label="Repeats">
                <KindSelect value={add.recurrence}
                  onChange={(v) => setAdd((a) => ({ ...a, recurrence: v as "ONCE" | "WEEKLY" }))}
                  options={[["ONCE", "One-off (selected days)"], ["WEEKLY", "Weekly"]]} />
              </Field>
              {add.recurrence === "ONCE" ? (
                <SelectedDaysHint count={selected.size} />
              ) : (
                <Field label="Days">
                  <div className="flex flex-wrap gap-1">
                    {DOW.map((d) => {
                      const on = add.days.has(d.n);
                      return (
                        <Button key={d.n} type="button" size="sm" variant={on ? "default" : "outline"}
                          className="h-8 w-11 px-0"
                          onClick={() => setAdd((a) => {
                            const days = new Set(a.days);
                            on ? days.delete(d.n) : days.add(d.n);
                            return { ...a, days };
                          })}>{d.label}</Button>
                      );
                    })}
                  </div>
                </Field>
              )}
              <p className="text-[11px] text-muted-foreground">
                Runs the selected shift's hours and crew on those days. Attended machines
                open too; lights-out machines already run 24/7; plant closures still win.
              </p>
              <Field label="Note (optional)">
                <Input value={add.reason} onChange={(e) => setAdd((a) => ({ ...a, reason: e.target.value }))} />
              </Field>
            </div>
          ) : (
            <div className="grid gap-3">
              <Field label="Who's out">
                <Select value={add.who || "ALL"} onValueChange={(v) => setAdd((a) => ({ ...a, who: v === "ALL" ? "" : v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">Whole company</SelectItem>
                    {users.map((u) => (
                      <SelectItem key={u.id} value={String(u.id)}>
                        {u.full_name || u.username}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Kind">
                <KindSelect value={add.laborKind} onChange={(v) => setAdd((a) => ({ ...a, laborKind: v }))}
                  options={[["PTO", "PTO / vacation"], ["SICK", "Sick"], ["TRAINING", "Training"], ["MEETING", "Meeting"], ["BREAK", "Break"], ["OTHER", "Other"]]} />
              </Field>
              <Field label="Repeats">
                <KindSelect value={add.recurrence} onChange={(v) => setAdd((a) => ({ ...a, recurrence: v as "ONCE" | "WEEKLY" }))}
                  options={[["ONCE", "One-off (selected days)"], ["WEEKLY", "Weekly"]]} />
              </Field>
              {add.recurrence === "ONCE" ? (
                <SelectedDaysHint count={selected.size} />
              ) : (
                <>
                  <Field label="Days">
                    <div className="flex flex-wrap gap-1">
                      {DOW.map((d) => {
                        const on = add.days.has(d.n);
                        return (
                          <Button key={d.n} type="button" size="sm" variant={on ? "default" : "outline"}
                            className="h-8 w-11 px-0"
                            onClick={() => setAdd((a) => {
                              const days = new Set(a.days);
                              on ? days.delete(d.n) : days.add(d.n);
                              return { ...a, days };
                            })}>{d.label}</Button>
                        );
                      })}
                    </div>
                  </Field>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="From">
                      <Input type="time" value={add.windowStart}
                        onChange={(e) => setAdd((a) => ({ ...a, windowStart: e.target.value }))} />
                    </Field>
                    <Field label="To">
                      <Input type="time" value={add.windowEnd}
                        onChange={(e) => setAdd((a) => ({ ...a, windowEnd: e.target.value }))} />
                    </Field>
                  </div>
                </>
              )}
              <Field label="Note (optional)">
                <Input value={add.reason} onChange={(e) => setAdd((a) => ({ ...a, reason: e.target.value }))} />
              </Field>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setAdd(initialAdd())}>Cancel</Button>
            <Button onClick={submit} disabled={!canSubmit || createClosure.isPending || createBlock.isPending}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}

function KindSelect({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: [string, string][];
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger><SelectValue /></SelectTrigger>
      <SelectContent>
        {options.map(([v, label]) => <SelectItem key={v} value={v}>{label}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

function SelectedDaysHint({ count }: { count: number }) {
  return (
    <p className="text-[11px] text-muted-foreground">
      {count === 0
        ? "Pick one or more days on the calendar first."
        : `Applies to the ${count} selected day${count === 1 ? "" : "s"} (earliest → latest).`}
    </p>
  );
}

function ListCard({ title, empty, children }: {
  title: string; empty: string; children: React.ReactNode;
}) {
  const arr = Array.isArray(children) ? children.filter(Boolean) : (children ? [children] : []);
  const hasItems = arr.length > 0;
  return (
    <div className="rounded-lg border p-3">
      <h4 className="mb-2 text-sm font-medium">{title}</h4>
      {hasItems ? <div className="space-y-1.5">{children}</div>
        : <p className="text-xs text-muted-foreground">{empty}</p>}
    </div>
  );
}

function Row({ label, sub, color, onDelete }: {
  label: string; sub: string; color: string; onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="min-w-0 flex-1">
        <div className="truncate">{label}</div>
        <div className="truncate text-[11px] text-muted-foreground">{sub}</div>
      </div>
      <Button size="icon" variant="ghost" className="h-7 w-7 shrink-0" onClick={onDelete}>
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function fmtDate(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : format(d, "MMM d");
}
function sameDay(a?: string | null, b?: string | null) {
  if (!a || !b) return true;
  const da = new Date(a), db = new Date(b);
  return isSameDay(da, db) || isSameDay(da, new Date(db.getTime() - 1000));
}
function weeklyDays(csv?: string | null) {
  if (!csv) return "";
  const map: Record<string, string> = { "0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat" };
  return csv.split(",").map((n) => map[n.trim()] ?? n).join(", ");
}

export default SchedulingCalendarPage;
