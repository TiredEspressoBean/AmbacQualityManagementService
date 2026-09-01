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
  useCalendarMonth,
  useCalendarYear,
  type Feature,
} from "@/components/kibo-ui/calendar";
import { CrewWallChart, type WallBand, type WallRow } from "@/components/scheduling/CrewWallChart";
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
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

const KIND_COLOR: Record<string, string> = {
  // closures
  HOLIDAY: "#ef4444", SHUTDOWN: "#dc2626", INVENTORY: "#f97316",
  // labor blocks
  PTO: "#f59e0b", SICK: "#fb923c", TRAINING: "#8b5cf6",
  MEETING: "#3b82f6", BREAK: "#64748b", OTHER: "#9ca3af",
  // additive
  OVERTIME: "#22c55e",
  // company-lens aggregate ("N out") — deliberately muted: it's a density
  // signal, the drill-down (crew/person lens or day click) carries the names
  OUT: "#64748b",
};
// Day numbering follows the MODEL/solver convention: 0=Monday .. 6=Sunday
// (Python `date.weekday()`), matching Shift.days_of_week and the shifts tab.
// NOT JavaScript's getDay() (0=Sunday) — using that here once shifted every
// FE-authored weekly block a day off in the solver.
const DOW = [
  { n: "0", label: "Mon" }, { n: "1", label: "Tue" }, { n: "2", label: "Wed" },
  { n: "3", label: "Thu" }, { n: "4", label: "Fri" }, { n: "5", label: "Sat" },
  { n: "6", label: "Sun" },
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

  // Calendar inputs (closures / labor blocks / overtime) are solver working-window
  // data — planner tier. Everyone can view the calendar; only planners author it.
  const { hasAny } = usePermissionSet();
  const canPlan = hasAny(
    "add_plantcalendarexception", "add_laborcalendarblock", "add_overtimewindow");

  // ── Scope: presets + composable filters ─────────────────────────────────────
  // Visibility matches blast radius: the COMPANY lens shows closures/overtime
  // plus a per-day "N out" density chip (no names — a day cell is tiny and a
  // person's PTO isn't plant-wide news); narrowing by crew (shift — the default
  // crew notion, since rosters/overtime/windows all hang off Shift), work
  // center, or person switches to named absences. Presets are one-click filter
  // combos; the filters still compose freely underneath.
  const { data: me } = useAuthUser();
  const [shiftFilter, setShiftFilter] = useState<string>("");   // shift id | ""
  const [wcFilter, setWcFilter] = useState<string>("");         // work-center id | ""
  const [personFilter, setPersonFilter] = useState<string>(""); // user id | ""
  const narrowed = Boolean(shiftFilter || wcFilter || personFilter);
  const myShiftId = (me as { default_shift?: string | null } | undefined)?.default_shift ?? null;
  const preset: "company" | "crew" | "me" | "custom" =
    !narrowed ? "company"
      : personFilter && String(personFilter) === String(me?.pk ?? "") && !shiftFilter && !wcFilter ? "me"
        : shiftFilter && String(shiftFilter) === String(myShiftId ?? "") && !wcFilter && !personFilter ? "crew"
          : "custom";
  const applyPreset = (p: "company" | "crew" | "me") => {
    setShiftFilter(p === "crew" && myShiftId ? String(myShiftId) : "");
    setWcFilter("");
    setPersonFilter(p === "me" && me?.pk != null ? String(me.pk) : "");
  };

  // Work centers + memberships back the WC filter (station membership → people).
  const { data: wcPage } = useQuery({
    queryKey: ["work-centers", "calendar-filter"] as const,
    queryFn: () => api.api_WorkCenters_list({ queries: { limit: 100 } } as never) as Promise<{
      results?: Array<{ id: string; code: string; name: string }>
    }>,
  });
  const workCenters = wcPage?.results ?? [];
  const { data: membershipsPage } = useQuery({
    queryKey: ["userwc-memberships", "calendar-filter"] as const,
    enabled: Boolean(wcFilter),
    queryFn: () => api.api_UserWorkCenterMemberships_list({
      queries: { limit: 500 },
    } as never) as Promise<{ results?: Array<{ user: number; work_center: string }> }>,
  });
  const wcMemberIds = useMemo(() => {
    if (!wcFilter) return null;
    const rows = membershipsPage?.results ?? [];
    return new Set(rows.filter((m) => String(m.work_center) === wcFilter).map((m) => m.user));
  }, [wcFilter, membershipsPage]);

  /** Whether a personal block's owner is inside the current scope. */
  const inScope = (userId: number | null | undefined) => {
    if (userId == null) return true; // company-wide blocks are always in scope
    if (personFilter) return String(userId) === personFilter;
    if (wcFilter) return wcMemberIds?.has(userId) ?? false;
    if (shiftFilter) {
      const u = users.find((x) => x.id === userId) as { default_shift?: string | null } | undefined;
      return String(u?.default_shift ?? "") === shiftFilter;
    }
    return true;
  };

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [add, setAdd] = useState<AddState>(initialAdd);
  const [viewedYear] = useCalendarYear();
  const [viewedMonth] = useCalendarMonth();

  // Crew/station scope renders the WALL CHART (people-rows × day-columns) —
  // the industry-standard "who's out, when" artifact — instead of the month
  // grid, whose day cells can't carry named absences. Person scope stays on
  // the month grid (sparse enough for named chips).
  const crewScope = Boolean((shiftFilter || wcFilter) && !personFilter);

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
    // Personal absences: named features only under a narrowed scope (crew /
    // station / person). The company lens collapses them to a per-day density
    // chip — "N out" — because a specific person's PTO isn't plant-wide news
    // and the day cell has no room for a roster.
    const aggregate = new Map<string, number>(); // dayKey -> distinct people out
    for (const b of blocks) {
      if (!b.is_active || b.recurrence !== "ONCE" || !b.start_time || !b.end_time) continue;
      if (b.user == null || narrowed) {
        if (!inScope(b.user)) continue;
        const label = b.user == null ? `Everyone: ${b.kind}` : `${userName(b.user)}: ${b.kind}`;
        out.push(...spanFeatures(String(b.id), label, b.kind || "OTHER",
          b.start_time as string, b.end_time as string));
      } else {
        const s = startOfDay(new Date(b.start_time as string));
        const e = startOfDay(new Date(b.end_time as string));
        if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime()) || e < s) continue;
        for (const d of eachDayOfInterval({ start: s, end: e })) {
          const k = dayKey(d);
          aggregate.set(k, (aggregate.get(k) ?? 0) + 1);
        }
      }
    }
    for (const [k, n] of aggregate) {
      out.push({
        id: `out-${k}`, name: `${n} out`,
        startAt: new Date(`${k}T00:00:00`), endAt: new Date(`${k}T00:00:00`),
        status: { id: "OUT", name: "OUT", color: KIND_COLOR.OUT },
      });
    }
    for (const o of overtimes) {
      if (!o.is_active || o.recurrence !== "ONCE" || !o.start_date || !o.end_date) continue;
      out.push(...spanFeatures(String(o.id), `Overtime: ${o.shift_name ?? ""}`.trim(),
        "OVERTIME", o.start_date as string, o.end_date as string));
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closures, blocks, overtimes, users, viewedYear, narrowed, shiftFilter, wcFilter, personFilter, wcMemberIds]);

  // ── Wall-chart data (crew/station scope) ──────────────────────────────────
  const wall = useMemo(() => {
    if (!crewScope) return null;
    const daysInMonth = new Date(viewedYear, viewedMonth + 1, 0).getDate();
    const monthStart = new Date(viewedYear, viewedMonth, 1);
    const monthEnd = new Date(viewedYear, viewedMonth, daysInMonth, 23, 59, 59);
    const weekendDays = new Set<number>();
    for (let d = 1; d <= daysInMonth; d++) {
      const dow = new Date(viewedYear, viewedMonth, d).getDay();
      if (dow === 0 || dow === 6) weekendDays.add(d);
    }
    const now = new Date();
    const today =
      now.getFullYear() === viewedYear && now.getMonth() === viewedMonth ? now.getDate() : null;

    const clip = (s: Date, e: Date): [number, number] | null => {
      if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;
      if (e < monthStart || s > monthEnd) return null;
      const startDay = s < monthStart ? 1 : s.getDate();
      const endDay = e > monthEnd ? daysInMonth : e.getDate();
      return startDay <= endDay ? [startDay, endDay] : null;
    };

    // People in scope, one row each; bars = their one-off absences this month.
    const scopedUsers = users
      .filter((u) => inScope(u.id))
      .sort((a, b) => (a.full_name || a.username || "").localeCompare(b.full_name || b.username || ""));
    const rows: WallRow[] = scopedUsers.map((u) => ({
      id: String(u.id),
      name: u.full_name || u.username || `User ${u.id}`,
      bars: blocks
        .filter((b) => b.is_active && b.recurrence === "ONCE" && b.user === u.id
          && b.start_time && b.end_time)
        .flatMap((b) => {
          const span = clip(new Date(b.start_time as string), new Date(b.end_time as string));
          if (!span) return [];
          return [{
            key: String(b.id),
            startDay: span[0], endDay: span[1],
            color: KIND_COLOR[b.kind || "OTHER"],
            label: b.kind || "OUT",
            title: `${b.kind} · ${fmtDate(b.start_time)}${sameDay(b.start_time, b.end_time) ? "" : `–${fmtDate(b.end_time)}`}${b.reason ? ` · ${b.reason}` : ""}`,
          }];
        }),
    }));

    // Plant-wide column bands: closures (incl. YEARLY mapped onto this year),
    // company-wide one-off blocks, and overtime days.
    const bands: WallBand[] = [];
    const pushBand = (s: Date, e: Date, kind: WallBand["kind"], title: string) => {
      const span = clip(s, e);
      if (!span) return;
      for (let d = span[0]; d <= span[1]; d++) bands.push({ day: d, kind, title });
    };
    for (const c of closures) {
      if (!c.is_active) continue;
      const s = new Date(c.start_time as string);
      const e = new Date(c.end_time as string);
      if (c.recurrence === "YEARLY") {
        const dur = e.getTime() - s.getTime();
        const os = new Date(s); os.setFullYear(viewedYear);
        pushBand(os, new Date(os.getTime() + dur), "closure", c.name || "Closure");
      } else {
        pushBand(s, e, "closure", c.name || "Closure");
      }
    }
    for (const b of blocks) {
      if (!b.is_active || b.user != null || b.recurrence !== "ONCE" || !b.start_time || !b.end_time) continue;
      pushBand(new Date(b.start_time as string), new Date(b.end_time as string),
        "closure", `Everyone: ${b.kind}`);
    }
    for (const o of overtimes) {
      if (!o.is_active || o.recurrence !== "ONCE" || !o.start_date || !o.end_date) continue;
      pushBand(new Date(`${o.start_date}T00:00:00`), new Date(`${o.end_date}T00:00:00`),
        "overtime", `Overtime: ${o.shift_name ?? "shift"}`);
    }

    return { rows, bands, daysInMonth, weekendDays, today };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [crewScope, viewedYear, viewedMonth, users, blocks, closures, overtimes,
      shiftFilter, wcFilter, personFilter, wcMemberIds]);

  const recurring = useMemo(
    () => blocks.filter((b) => b.recurrence === "WEEKLY"),
    [blocks]
  );

  const toggleDay = (d: Date) => {
    const k = dayKey(d);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k); else next.add(k);
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
    // Wide cap: the crew wall chart needs ~29px/day × 31 + a name column; the
    // old max-w-6xl (1152px) pinned day columns at their 22px floor and forced
    // a horizontal scroll. Measured at 1707px viewport: 6xl left ~350px unused.
    <div className="mx-auto max-w-screen-2xl space-y-4 p-6">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Scheduling calendar</h1>
          <p className="text-sm text-muted-foreground">
            Plant closures and who's out — the non-working time the scheduler plans around.
            Click one or more days, then add a closure or absence.
          </p>
        </div>
      </div>

      {/* Scope: presets + composable filters. Company aggregates personal
          absences to a per-day "N out" chip; narrowing shows names. */}
      <div className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
        <div className="flex items-center rounded-md border p-0.5">
          {([["company", "Company"], ["crew", "My crew"], ["me", "Me"]] as const).map(([p, label]) => (
            <Button
              key={p}
              variant={preset === p ? "secondary" : "ghost"}
              size="sm"
              className="h-7 px-2 text-xs"
              disabled={p === "crew" && !myShiftId}
              title={p === "crew" && !myShiftId ? "You aren't rostered to a shift" : undefined}
              onClick={() => applyPreset(p)}
            >
              {label}
            </Button>
          ))}
        </div>
        <Select value={shiftFilter || "__all__"} onValueChange={(v) => setShiftFilter(v === "__all__" ? "" : v)}>
          <SelectTrigger className="h-8 w-40 text-xs"><SelectValue placeholder="Shift" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All shifts</SelectItem>
            {shifts.map((s) => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={wcFilter || "__all__"} onValueChange={(v) => setWcFilter(v === "__all__" ? "" : v)}>
          <SelectTrigger className="h-8 w-44 text-xs"><SelectValue placeholder="Work center" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All work centers</SelectItem>
            {workCenters.map((w) => <SelectItem key={w.id} value={String(w.id)}>{w.code} — {w.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={personFilter || "__all__"} onValueChange={(v) => setPersonFilter(v === "__all__" ? "" : v)}>
          <SelectTrigger className="h-8 w-44 text-xs"><SelectValue placeholder="Person" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">Everyone</SelectItem>
            {users.map((u) => (
              <SelectItem key={u.id} value={String(u.id)}>{u.full_name || u.username}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {!narrowed && (
          <span className="text-[11px] text-muted-foreground">
            Company view — absences show as “N out”; pick a crew, station, or person for names.
          </span>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {[["HOLIDAY", "Closure"], ["PTO", "PTO"], ["SICK", "Sick"], ["TRAINING", "Training"],
          ["MEETING", "Meeting"], ["BREAK", "Break"], ["OVERTIME", "Overtime"],
          ...(narrowed ? [] : [["OUT", "People out (count)"]]),
        ].map(([k, label]) => (
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
          {canPlan && (
            <>
              <Button size="sm" variant="outline" disabled={selected.size === 0}
                onClick={() => openAdd("closure")}>Add closure</Button>
              <Button size="sm" variant="outline" disabled={selected.size === 0}
                onClick={() => openAdd("labor")}>Add absence / meeting</Button>
              <Button size="sm" variant="outline" disabled={selected.size === 0}
                onClick={() => openAdd("overtime")}>Add overtime</Button>
              <Button size="sm" variant="ghost" onClick={() => openAdd("labor")}
                title="Add a recurring block without picking days">Add recurring…</Button>
            </>
          )}
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
            {crewScope && wall ? (
              <CrewWallChart
                rows={wall.rows}
                daysInMonth={wall.daysInMonth}
                weekendDays={wall.weekendDays}
                bands={wall.bands}
                today={wall.today}
                selectedDays={new Set(
                  [...selected]
                    .map((k) => new Date(`${k}T00:00:00`))
                    .filter((d) => d.getFullYear() === viewedYear && d.getMonth() === viewedMonth)
                    .map((d) => d.getDate())
                )}
                onDayClick={(d) => toggleDay(new Date(viewedYear, viewedMonth, d))}
              />
            ) : (
              <>
                <CalendarHeader />
                <CalendarBody features={features} onDayClick={toggleDay} selectedDates={selectedDates}>
                  {({ feature }) => <CalendarItem feature={feature} key={feature.id} />}
                </CalendarBody>
              </>
            )}
          </CalendarProvider>
        </div>

        {/* Management lists */}
        <div className="space-y-4">
          {/* Personal lens: agenda + week shape — for an individual, a list
              beats grid tweaks (and it's the natural mobile form). */}
          {preset === "me" && (
            <>
              <ListCard title="Your upcoming" empty="Nothing coming up in the next 45 days.">
                {(() => {
                  const now = new Date();
                  const horizon = new Date(now.getTime() + 45 * 24 * 3600 * 1000);
                  const items: { key: string; when: Date; label: string; sub: string; color: string }[] = [];
                  for (const b of blocks) {
                    if (!b.is_active || b.recurrence !== "ONCE" || b.user !== me?.pk || !b.start_time) continue;
                    const s = new Date(b.start_time as string);
                    if (s < now || s > horizon) continue;
                    items.push({
                      key: `b-${b.id}`, when: s, label: `${b.kind}`, color: KIND_COLOR[b.kind || "OTHER"],
                      sub: `${fmtDate(b.start_time)}${sameDay(b.start_time, b.end_time) ? "" : `–${fmtDate(b.end_time)}`}${b.reason ? ` · ${b.reason}` : ""}`,
                    });
                  }
                  for (const o of overtimes) {
                    if (!o.is_active || o.recurrence !== "ONCE" || !o.start_date) continue;
                    if (String(o.shift) !== String(myShiftId ?? "")) continue;
                    const s = new Date(`${o.start_date}T00:00:00`);
                    if (s < now || s > horizon) continue;
                    items.push({
                      key: `o-${o.id}`, when: s, label: "Overtime", color: KIND_COLOR.OVERTIME,
                      sub: `${fmtDate(o.start_date)}${o.reason ? ` · ${o.reason}` : ""}`,
                    });
                  }
                  for (const c of closures) {
                    if (!c.is_active || !c.start_time) continue;
                    const s = new Date(c.start_time as string);
                    if (c.recurrence === "YEARLY") s.setFullYear(now.getFullYear());
                    if (s < now || s > horizon) continue;
                    items.push({
                      key: `c-${c.id}`, when: s, label: c.name || "Closure",
                      color: KIND_COLOR[c.kind || "HOLIDAY"], sub: fmtDate(s.toISOString()),
                    });
                  }
                  return items
                    .sort((a, b2) => a.when.getTime() - b2.when.getTime())
                    .map((it) => (
                      <Row key={it.key} label={it.label} sub={it.sub} color={it.color}
                        onDelete={() => {}} canDelete={false} />
                    ));
                })()}
              </ListCard>
              {(() => {
                const myShift = (shifts as Array<{ id: string; name: string; start_time?: string;
                  end_time?: string; days_of_week?: string;
                  break_windows?: Array<{ start: string; end: string }> }>)
                  .find((s) => String(s.id) === String(myShiftId ?? ""));
                if (!myShift) return null;
                return (
                  <ListCard title="Your week" empty="">
                    <div className="space-y-1 text-sm">
                      <div>{myShift.name} · {myShift.start_time?.slice(0, 5)}–{myShift.end_time?.slice(0, 5)}</div>
                      <div className="text-xs text-muted-foreground">
                        {weeklyDays(myShift.days_of_week)}
                      </div>
                      {(myShift.break_windows ?? []).length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          Breaks: {(myShift.break_windows ?? [])
                            .map((b) => `${b.start.slice(0, 5)}–${b.end.slice(0, 5)}`).join(", ")}
                        </div>
                      )}
                    </div>
                  </ListCard>
                );
              })()}
            </>
          )}

          <ListCard title="Plant closures" empty="No closures.">
            {closures.filter((c) => c.is_active).map((c: PlantClosure) => (
              <Row key={c.id}
                label={c.name || "Closure"}
                sub={`${c.kind} · ${fmtDate(c.start_time)}${sameDay(c.start_time, c.end_time) ? "" : `–${fmtDate(c.end_time)}`}${c.recurrence === "YEARLY" ? " · yearly" : ""}`}
                color={KIND_COLOR[c.kind || "HOLIDAY"]}
                onDelete={() => delClosure.mutate(String(c.id))} canDelete={canPlan} />
            ))}
          </ListCard>

          {/* Drill-down: clicking day(s) is explicit intent — names show even
              in the company lens (scope filters still apply when narrowed). */}
          {selected.size > 0 && (
            <ListCard title="Out on selected days" empty="Nobody out on the selected days.">
              {blocks
                .filter((b) => b.recurrence === "ONCE" && b.is_active && b.user != null
                  && b.start_time && b.end_time && inScope(b.user)
                  && [...selected].some((k) => {
                    const d = new Date(`${k}T00:00:00`);
                    return startOfDay(new Date(b.start_time as string)) <= d
                      && d <= startOfDay(new Date(b.end_time as string));
                  }))
                .map((b: LaborBlock) => (
                  <Row key={`sel-${b.id}`}
                    label={`${userName(b.user)}: ${b.kind}`}
                    sub={`${fmtDate(b.start_time)}${sameDay(b.start_time, b.end_time) ? "" : `–${fmtDate(b.end_time)}`}`}
                    color={KIND_COLOR[b.kind || "OTHER"]}
                    onDelete={() => delBlock.mutate(String(b.id))} canDelete={canPlan} />
                ))}
            </ListCard>
          )}

          <ListCard title="Recurring blocks" empty="No recurring blocks.">
            {recurring.filter((b) => inScope(b.user)).map((b: LaborBlock) => (
              <Row key={b.id}
                label={`${userName(b.user)}: ${b.kind}`}
                sub={`Weekly ${weeklyDays(b.days_of_week)} · ${b.window_start ?? ""}–${b.window_end ?? ""}`}
                color={KIND_COLOR[b.kind || "OTHER"]}
                onDelete={() => delBlock.mutate(String(b.id))} canDelete={canPlan} />
            ))}
          </ListCard>

          <ListCard
            title="One-off absences"
            empty={narrowed ? "No one-off absences in this scope."
              : "Company view — narrow to a crew, station, or person (or click days) to see who's out."}
          >
            {(narrowed
              ? blocks.filter((b) => b.recurrence === "ONCE" && b.is_active && inScope(b.user))
              : blocks.filter((b) => b.recurrence === "ONCE" && b.is_active && b.user == null)
            ).map((b: LaborBlock) => (
              <Row key={b.id}
                label={`${userName(b.user)}: ${b.kind}`}
                sub={`${fmtDate(b.start_time)}${sameDay(b.start_time, b.end_time) ? "" : `–${fmtDate(b.end_time)}`}`}
                color={KIND_COLOR[b.kind || "OTHER"]}
                onDelete={() => delBlock.mutate(String(b.id))} canDelete={canPlan} />
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
                onDelete={() => delOvertime.mutate(String(o.id))} canDelete={canPlan} />
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
                            if (on) days.delete(d.n); else days.add(d.n);
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
                              if (on) days.delete(d.n); else days.add(d.n);
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

function Row({ label, sub, color, onDelete, canDelete = true }: {
  label: string; sub: string; color: string; onDelete: () => void; canDelete?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <div className="min-w-0 flex-1">
        <div className="truncate">{label}</div>
        <div className="truncate text-[11px] text-muted-foreground">{sub}</div>
      </div>
      {canDelete && (
        <Button size="icon" variant="ghost" className="h-7 w-7 shrink-0" onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}

function fmtDate(iso?: string | null) {
  if (!iso) return "";
  // Date-only strings (e.g. OvertimeWindow.start_date "2026-09-05") must parse
  // as LOCAL dates — bare `new Date("YYYY-MM-DD")` treats them as UTC midnight,
  // which renders a day early for anyone west of Greenwich.
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : format(d, "MMM d");
}
function sameDay(a?: string | null, b?: string | null) {
  if (!a || !b) return true;
  const da = new Date(a), db = new Date(b);
  return isSameDay(da, db) || isSameDay(da, new Date(db.getTime() - 1000));
}
function weeklyDays(csv?: string | null) {
  if (!csv) return "";
  // Model convention: 0=Monday .. 6=Sunday (see DOW above).
  const map: Record<string, string> = { "0": "Mon", "1": "Tue", "2": "Wed", "3": "Thu", "4": "Fri", "5": "Sat", "6": "Sun" };
  return csv.split(",").map((n) => map[n.trim()] ?? n).join(", ");
}

export default SchedulingCalendarPage;
