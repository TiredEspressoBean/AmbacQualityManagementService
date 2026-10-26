/**
 * Plan vs actual — did the floor follow the schedule? (Planner track module 8; decided
 * 2026-10-26 from the /dev mock.)
 *
 *  - A finished op is drawn at its ACTUAL start/end; a running op from its actual start
 *    to now.
 *  - Colour = actual finish against the PLANNED finish as it stood when the op started
 *    (frozen server-side, so a re-solve can't hide a slip): green within ±tolerance,
 *    blue early beyond it, amber late, red very late.
 *  - Due but never started: a red dashed outline at its planned slot.
 *  - Started before any schedule had it (work in hand at a first solve or a
 *    regenerate): drawn at its actual times, uncoloured, outside the adherence figure —
 *    there is no plan to judge it by.
 *  - Ops still to come: from the live schedule, as the board draws them.
 *  - Optional (off by default): a mark on ops started well ahead of their planned start.
 *
 * Done, running and missed ops come from /Schedules/adherence/ — every schedule that
 * was live in the last 7 days, since a re-solve drops finished work from the live one.
 * One bar per shared cycle (×N), sub-rows wherever bars overlap. Only bars in view are
 * rendered; the headline counts cover the whole window.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    GanttProvider, GanttTimeline, GanttHeader, GanttFeatureList, GanttFeatureItem, GanttToday,
    type GanttFeature,
} from "@/components/kibo-ui/gantt";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api/generated";

type LiveTask = {
    id: string;
    part_erp: string | null;
    core_number: string | null;
    step_name: string | null;
    machine_name: string | null;
    operator_name: string | null;
    work_order: string | null;
    is_outside_process: boolean;
    is_late: boolean;
    start_time: string;
    end_time: string;
    actual_start: string | null;
};

type AdherenceOp = {
    id: string;
    state: "done" | "running" | "missed";
    /** False: started before any schedule had it — no plan to judge it by. */
    judged: boolean;
    planned_start: string;
    planned_end: string;
    actual_start: string | null;
    actual_end: string | null;
    part_erp: string | null;
    work_order: string | null;
    step_name: string | null;
    machine_name: string | null;
    operator_name: string | null;
};

// unplanned: finished, but started before any schedule had it — drawn, never judged.
type Kind = "ontime" | "early" | "late" | "verylate" | "missed" | "running" | "unplanned" | "future";

type Op = {
    id: string;
    lane: string;
    label: string;
    count: number;
    plannedStart: Date;
    plannedEnd: Date;
    actualStart: Date | null;
    actualEnd: Date | null;
    kind: Kind;
    deviation: number | null;
    judged: boolean;
    outOfOrder: boolean;
    isLate: boolean;
};

const MIN = 60_000;
const DAY = 24 * 60 * MIN;
const ROW_PX = 36;
const WINDOW_DAYS = 7;

const fmtTime = (d: Date) => d.toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" });
const fmtDev = (m: number) => `${m > 0 ? "+" : m < 0 ? "−" : "±"}${Math.abs(Math.round(m))} min`;
const startOfDay = (t: number) => { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); };

function classify(dev: number, tolerance: number, redAfter: number): Kind {
    if (Math.abs(dev) <= tolerance) return "ontime";
    if (dev < 0) return "early";
    return dev > redAfter ? "verylate" : "late";
}

const STYLE: Record<Kind, string> = {
    ontime: "bg-emerald-100 text-emerald-900 ring-1 ring-inset ring-emerald-400 dark:bg-emerald-950 dark:text-emerald-200",
    early: "bg-sky-100 text-sky-900 ring-1 ring-inset ring-sky-400 dark:bg-sky-950 dark:text-sky-200",
    late: "bg-amber-100 text-amber-900 ring-1 ring-inset ring-amber-400 dark:bg-amber-950 dark:text-amber-200",
    verylate: "bg-red-200 text-red-950 ring-1 ring-inset ring-red-500 dark:bg-red-950 dark:text-red-200",
    missed: "bg-transparent text-red-600 shadow-none border-2 border-dashed border-red-500",
    running: "bg-violet-100 text-violet-900 ring-2 ring-inset ring-violet-500 dark:bg-violet-950 dark:text-violet-200",
    unplanned: "bg-muted text-muted-foreground ring-1 ring-inset ring-border",
    future: "",
};

const LEGEND: { kind: Kind; label: string }[] = [
    { kind: "ontime", label: "On time" },
    { kind: "early", label: "Early" },
    { kind: "late", label: "Late" },
    { kind: "verylate", label: "Very late" },
    { kind: "missed", label: "Due, never started" },
    { kind: "running", label: "Running" },
    { kind: "unplanned", label: "Started before planned" },
];

export function PlanVsActualView({ liveTasks, groupBy, zoom }: {
    /** The live schedule's tasks — the ops still to come. */
    liveTasks: LiveTask[];
    groupBy: "machine" | "operator";
    zoom: number;
}) {
    const rootRef = useRef<HTMLDivElement>(null);
    const [tolerance, setTolerance] = useState(15);
    const [redAfter, setRedAfter] = useState(60);
    const [showOutOfOrder, setShowOutOfOrder] = useState(false);
    const [selected, setSelected] = useState<string | null>(null);
    const [now, setNow] = useState(() => Date.now());
    useEffect(() => {
        const t = setInterval(() => setNow(Date.now()), 60_000);
        return () => clearInterval(t);
    }, []);

    const { data: adherence, isLoading } = useQuery({
        queryKey: ["schedule-adherence", WINDOW_DAYS],
        queryFn: () => api.api_Schedules_adherence_list({ queries: { days: WINDOW_DAYS } }) as Promise<AdherenceOp[]>,
        refetchInterval: 60_000,
    });

    const laneOf = (machine: string | null, operator: string | null) => groupBy === "machine"
        ? (machine ?? `— no machine · ${operator ?? "unassigned"}`)
        : (operator ?? "— unassigned");

    // One op per cycle: a lane's work for one work order and step in one planned slot.
    const ops = useMemo((): Op[] => {
        type Unit = {
            id: string; lane: string; what: string; step: string; ps: number; pe: number;
            as: number | null; ae: number | null; state: "done" | "running" | "missed" | "future"; late: boolean;
            judged: boolean;
        };
        const units: Unit[] = [];
        const seen = new Set<string>();
        for (const a of adherence ?? []) {
            seen.add(a.id);
            units.push({
                id: a.id, lane: laneOf(a.machine_name, a.operator_name),
                what: groupBy === "machine" ? (a.work_order ?? a.part_erp ?? "job") : (a.machine_name ?? "—"),
                step: a.step_name ?? "", ps: new Date(a.planned_start).getTime(), pe: new Date(a.planned_end).getTime(),
                as: a.actual_start ? new Date(a.actual_start).getTime() : null,
                ae: a.actual_end ? new Date(a.actual_end).getTime() : null, state: a.state, late: false,
                judged: a.judged,
            });
        }
        for (const t of liveTasks) {
            if (seen.has(t.id) || t.actual_start || t.is_outside_process) continue;
            units.push({
                id: t.id, lane: laneOf(t.machine_name, t.operator_name),
                what: groupBy === "machine" ? (t.work_order ?? t.part_erp ?? t.core_number ?? "job") : (t.machine_name ?? "—"),
                step: t.step_name ?? "", ps: new Date(t.start_time).getTime(), pe: new Date(t.end_time).getTime(),
                as: null, ae: null, state: "future", late: t.is_late, judged: true,
            });
        }
        const cycles = new Map<string, Unit[]>();
        for (const u of units) {
            // A cycle shares its slot: the same planned start, or the same actual start.
            const key = `${u.lane}::${u.what}::${u.step}::${u.state}::${u.judged}::${u.as ?? u.ps}`;
            (cycles.get(key) ?? cycles.set(key, []).get(key)!).push(u);
        }
        return [...cycles.entries()].map(([key, us]) => {
            const u = us[0];
            const pe = Math.max(...us.map((x) => x.pe));
            const ae = us.every((x) => x.ae != null) ? Math.max(...us.map((x) => x.ae!)) : null;
            const op: Op = {
                id: key, lane: u.lane, count: us.length,
                label: `${u.what} · ${u.step}${us.length > 1 ? ` ×${us.length}` : ""}`,
                plannedStart: new Date(u.ps), plannedEnd: new Date(pe),
                actualStart: u.as != null ? new Date(u.as) : null, actualEnd: ae != null ? new Date(ae) : null,
                kind: "future", deviation: null, judged: u.judged, outOfOrder: false,
                isLate: us.some((x) => x.late),
            };
            if (u.state === "missed") return { ...op, kind: "missed" };
            const early = u.judged && u.as != null && u.as < u.ps - Math.max(60, 2 * tolerance) * MIN;
            if (u.state === "running") return { ...op, kind: "running", outOfOrder: early };
            if (u.state === "done" && !u.judged) return { ...op, kind: "unplanned" };
            if (u.state === "done" && ae != null) {
                const deviation = (ae - pe) / MIN;
                return { ...op, deviation, kind: classify(deviation, tolerance, redAfter), outOfOrder: early };
            }
            return op;
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [adherence, liveTasks, groupBy, tolerance, redAfter]);

    // The window's first midnight, fixed for the life of the view: a moving boundStart
    // re-runs the provider's initial scroll and throws the view back to the start.
    const [windowStart] = useState(() => startOfDay(Date.now() - WINDOW_DAYS * DAY));
    // Work running since before the window is drawn from the window's start.
    const drawn = (o: Op) => (o.kind === "missed" || o.kind === "future"
        ? { startAt: o.plannedStart, endAt: o.plannedEnd }
        : { startAt: new Date(Math.max(o.actualStart!.getTime(), windowStart)), endAt: o.actualEnd ?? new Date(now) });

    const lanes = useMemo(() => {
        const m = new Map<string, Op[]>();
        for (const o of ops) (m.get(o.lane) ?? m.set(o.lane, []).get(o.lane)!).push(o);
        return [...m.entries()]
            .sort(([a], [b]) => (a.startsWith("—") ? 1 : 0) - (b.startsWith("—") ? 1 : 0) || a.localeCompare(b))
            .map(([name, laneOps]) => {
                const rows: Op[][] = [];
                const ends: number[] = [];
                for (const o of [...laneOps].sort((x, y) => drawn(x).startAt.getTime() - drawn(y).startAt.getTime())) {
                    const { startAt, endAt } = drawn(o);
                    const i = ends.findIndex((e) => e <= startAt.getTime());
                    if (i >= 0) { rows[i].push(o); ends[i] = endAt.getTime(); } else { rows.push([o]); ends.push(endAt.getTime()); }
                }
                return { name, count: laneOps.reduce((n, o) => n + o.count, 0), rows };
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [ops, now]);

    // The headline covers everything due in the window, on screen or not.
    const counts = useMemo(() => {
        const c: Record<Kind, number> = {
            ontime: 0, early: 0, late: 0, verylate: 0, missed: 0, running: 0, unplanned: 0, future: 0,
        };
        ops.forEach((o) => { c[o.kind] += 1; });
        const due = c.ontime + c.early + c.late + c.verylate + c.missed;
        return { ...c, due, adherence: due ? Math.round(((c.ontime + c.early) / due) * 100) : null };
    }, [ops]);

    const boundEndMs = useMemo(
        () => Math.max(now + DAY, ...ops.map((o) => o.plannedEnd.getTime())) + 30 * MIN,
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [ops]);
    const bounds = useMemo(() => ({ start: new Date(windowStart), end: new Date(boundEndMs) }),
        [windowStart, boundEndMs]);
    const [openedAt] = useState(() => new Date());

    // Virtualize: render only bars in the visible time window (+ one screen each side).
    const dayPx = (720 * zoom) / 100;
    const [viewport, setViewport] = useState({ scrollLeft: 0, clientWidth: 4000 });
    useEffect(() => {
        const el = rootRef.current?.querySelector(".gantt") as HTMLElement | null;
        if (!el) return;
        const read = () => setViewport((v) => {
            const clientWidth = el.clientWidth || v.clientWidth;
            return v.scrollLeft === el.scrollLeft && v.clientWidth === clientWidth ? v : { scrollLeft: el.scrollLeft, clientWidth };
        });
        read();
        el.addEventListener("scroll", read, { passive: true });
        const ro = new ResizeObserver(read);
        ro.observe(el);
        return () => { el.removeEventListener("scroll", read); ro.disconnect(); };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isLoading]);
    const inView = (o: Op) => {
        const { startAt, endAt } = drawn(o);
        const origin = bounds.start.getTime();
        const l = ((startAt.getTime() - origin) / DAY) * dayPx;
        const r = ((endAt.getTime() - origin) / DAY) * dayPx;
        return r >= viewport.scrollLeft - viewport.clientWidth && l <= viewport.scrollLeft + 2 * viewport.clientWidth;
    };

    const describe = (o: Op) => {
        const planned = `planned ${fmtTime(o.plannedStart)}–${fmtTime(o.plannedEnd)}`;
        if (o.kind === "missed") return `${planned} · never started`;
        if (!o.judged && o.actualStart) {
            const ran = `started ${fmtTime(o.actualStart)}${o.actualEnd ? `, finished ${fmtTime(o.actualEnd)}` : ", running"}`;
            return `${ran} · started before it was planned, so not judged`;
        }
        if (o.kind === "running" && o.actualStart) return `${planned} · started ${fmtTime(o.actualStart)}, running`;
        if (o.actualStart && o.actualEnd && o.deviation != null)
            return `${planned} · actual ${fmtTime(o.actualStart)}–${fmtTime(o.actualEnd)} · ${fmtDev(o.deviation)}`;
        return planned;
    };
    const toFeature = (o: Op): GanttFeature => ({
        id: o.id, name: o.label, ...drawn(o), status: { id: o.kind, name: o.kind, color: "#94a3b8" },
    });
    const selectedOp = selected ? ops.find((o) => o.id === selected) ?? null : null;

    if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Loading what happened…</div>;

    return (
        <div ref={rootRef} className="flex min-h-0 flex-1 flex-col gap-2">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                    {LEGEND.map((l) => (
                        <span key={l.kind} className={`rounded px-2 py-0.5 ${STYLE[l.kind]}`}>{l.label} · {counts[l.kind]}</span>
                    ))}
                    <span className="rounded px-2 py-0.5 ring-1 ring-inset ring-border">To come · {counts.future}</span>
                    <span className="ml-2 text-muted-foreground">
                        {counts.adherence == null
                            ? `Nothing was due in the last ${WINDOW_DAYS} days.`
                            : <>Adherence: <strong className="text-foreground">{counts.adherence}%</strong> of {counts.due} ops due in the last {WINDOW_DAYS} days finished on time or early</>}
                    </span>
                </div>
                <div className="flex flex-wrap items-end gap-3">
                    <div className="space-y-1">
                        <Label htmlFor="pva-tol" className="text-xs">On time within ± (min)</Label>
                        <Input id="pva-tol" type="number" min={0} className="h-8 w-24" value={tolerance}
                            onChange={(e) => setTolerance(Math.max(0, Number(e.target.value) || 0))} />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="pva-red" className="text-xs">Very late after (min)</Label>
                        <Input id="pva-red" type="number" min={0} className="h-8 w-24" value={redAfter}
                            onChange={(e) => setRedAfter(Math.max(tolerance, Number(e.target.value) || 0))} />
                    </div>
                    <label className="flex items-center gap-2 pb-1 text-xs">
                        <Switch checked={showOutOfOrder} onCheckedChange={setShowOutOfOrder} />
                        Mark out-of-order starts
                    </label>
                </div>
            </div>

            {selectedOp && (
                <div className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-sm">
                    <span><strong>{selectedOp.label}</strong> · {describe(selectedOp)}{selectedOp.outOfOrder ? " · started ahead of plan" : ""}</span>
                    <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>Close</Button>
                </div>
            )}

            <GanttProvider range="hourly" zoom={zoom} boundStart={bounds.start} boundEnd={bounds.end}
                initialCenter={openedAt}
                className="min-h-0 flex-1 rounded-lg border">
                <div data-roadmap-ui="gantt-sidebar"
                    className="sticky left-0 z-30 h-max min-h-full overflow-clip border-r border-border/50 bg-background/90 backdrop-blur-md">
                    <div className="sticky top-0 z-10 flex items-end justify-between gap-2.5 border-b border-border/50 p-2.5 text-xs font-medium text-muted-foreground"
                        style={{ height: "var(--gantt-header-height)" }}>
                        <span className="flex-1 truncate">{groupBy === "machine" ? "Machine" : "Person"}</span>
                        <span className="shrink-0">Ops</span>
                    </div>
                    {lanes.map((l) => (
                        <div key={l.name} className="flex items-start gap-2 border-b border-border/30 px-2.5 pt-2.5 text-xs font-medium text-muted-foreground"
                            style={{ height: l.rows.length * ROW_PX }}>
                            <span className="flex-1 truncate" title={l.name}>{l.name}</span>
                            <span className="shrink-0 tabular-nums">{l.count}</span>
                        </div>
                    ))}
                </div>
                <GanttTimeline>
                    <GanttHeader />
                    <GanttFeatureList>
                        {lanes.map((l) => (
                            <div key={l.name} className="border-b border-border/30">
                                {l.rows.map((row, i) => (
                                    <div key={i} className="relative w-max min-w-full py-0.5" style={{ height: ROW_PX }}>
                                        {row.filter(inView).map((o) => {
                                            const ooo = showOutOfOrder && o.outOfOrder;
                                            return (
                                                <GanttFeatureItem key={o.id} {...toFeature(o)} bare
                                                    onSelect={(id) => setSelected(id)}
                                                    cardClassName={[
                                                        STYLE[o.kind],
                                                        o.kind === "future" && o.isLate ? "ring-2 ring-inset ring-red-500 text-red-600" : "",
                                                        ooo ? "outline outline-2 outline-fuchsia-500" : "",
                                                        selected === o.id ? "ring-2 ring-sky-600" : "",
                                                    ].join(" ")}>
                                                    <p className="flex-1 truncate text-xs" title={`${o.label}\n${describe(o)}${o.outOfOrder ? "\nstarted ahead of plan" : ""}`}>
                                                        {ooo ? "⇤ " : ""}{o.kind === "running" ? "▶ " : ""}{o.label}
                                                    </p>
                                                </GanttFeatureItem>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        ))}
                    </GanttFeatureList>
                    <GanttToday />
                </GanttTimeline>
            </GanttProvider>
        </div>
    );
}
