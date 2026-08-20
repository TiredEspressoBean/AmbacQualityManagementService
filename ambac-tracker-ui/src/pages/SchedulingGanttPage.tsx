// Production schedule Gantt — reads the active CP-SAT schedule and renders it,
// grouped by machine / operator / product, with solve / dispatch actions, search,
// and a per-task detail dialog (opened from the bar) that pins/unpins.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { differenceInMinutes, startOfDay } from "date-fns";
import { toast } from "sonner";
import { ChevronRight, Pin, PinOff, Search, ZoomIn, ZoomOut } from "lucide-react";
import {
  GanttProvider,
  GanttSidebar,
  GanttSidebarItem,
  GanttTimeline,
  GanttHeader,
  GanttFeatureList,
  GanttFeatureListGroup,
  GanttFeatureItem,
  GanttShiftBands,
  GanttPegLines,
  GanttToday,
  type GanttFeature,
} from "@/components/kibo-ui/gantt";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useCurrentSchedule,
  useScheduledTasks,
  useSolveSchedule,
  useSolveDraft,
  useDraftSchedule,
  useCompareDraft,
  useCommitDraft,
  useDiscardDraft,
  useDispatchSchedule,
  usePinTask,
  useMoveTask,
  useMoveBatch,
  usePinBatch,
  useWorkingWindows,
} from "@/hooks/useScheduling";

const FENCE = {
  frozen: { name: "Frozen", color: "#ef4444" },
  slushy: { name: "Slushy", color: "#f59e0b" },
  liquid: { name: "Liquid", color: "#22c55e" },
} as const;

const ZOOM_MIN = 30;
const ZOOM_MAX = 1500;
const clampZoom = (z: number) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(z)));

/** Stable key for the unit (part or core) a task belongs to — one job's route. */
const unitKey = (t: { part_erp: string | null; core_number: string | null }) =>
  t.part_erp ? `p:${t.part_erp}` : t.core_number ? `c:${t.core_number}` : null;

/** A merged work-order batch on a lane (many parts of one WO at one operation). */
type BatchMeta = {
  work_order: string | null;
  step_name: string | null;
  machine_name: string | null;
  work_center: string | null;
  count: number;
  taskIds: string[];
  startAt: Date;
  endAt: Date;
  anyLate: boolean;
  allPinned: boolean;
};

const isBatchId = (id: string) => id.startsWith("batch:");

type Task = {
  id: string;
  part_erp: string | null;
  core_number: string | null;
  step_name: string | null;
  machine_name: string | null;
  operator_name: string | null;
  work_order: string | null;
  work_center: string | null;
  requires_operator: boolean;
  due_date: string | null;
  is_late: boolean;
  start_time: string;
  end_time: string;
  is_pinned: boolean;
  fence_zone: keyof typeof FENCE;
};

type CompareSummary = {
  schedule_id: string;
  solver_status: string;
  weighted_lateness: number;
  makespan_minutes: number;
  task_count: number;
  uncovered: number;
};
type CompareResult = { live: CompareSummary | null; draft: CompareSummary | null; moved: number };

/** Banner comparing the pending what-if draft to the live schedule, with commit/discard. */
function DraftCompareBar({
  compare,
  committing,
  discarding,
  onCommit,
  onDiscard,
}: {
  compare?: CompareResult;
  committing: boolean;
  discarding: boolean;
  onCommit: () => void;
  onDiscard: () => void;
}) {
  const l = compare?.live;
  const d = compare?.draft;
  const hrs = (m?: number) => (m == null ? "—" : (m / 60).toFixed(1));
  const deltaCls = (delta: number | null) =>
    delta == null || delta === 0
      ? "text-muted-foreground"
      : delta < 0
        ? "text-green-600 dark:text-green-400" // lower makespan/lateness is better
        : "text-red-600 dark:text-red-400";
  const dMakespan = l && d ? d.makespan_minutes - l.makespan_minutes : null;
  const dLateness = l && d ? d.weighted_lateness - l.weighted_lateness : null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-medium text-amber-700 dark:text-amber-400">
          What-if draft — review vs live
        </span>
        <span>
          makespan <span className="text-muted-foreground">{hrs(l?.makespan_minutes)} → </span>
          <span className="font-medium">{hrs(d?.makespan_minutes)} h</span>
          {dMakespan != null && dMakespan !== 0 && (
            <span className={"ml-1 " + deltaCls(dMakespan)}>
              ({dMakespan > 0 ? "+" : ""}
              {(dMakespan / 60).toFixed(1)} h)
            </span>
          )}
        </span>
        <span>
          lateness{" "}
          <span className="text-muted-foreground">
            {(l?.weighted_lateness ?? 0).toLocaleString()} →{" "}
          </span>
          <span className="font-medium">{(d?.weighted_lateness ?? 0).toLocaleString()}</span>
          {dLateness != null && dLateness !== 0 && (
            <span className={"ml-1 " + deltaCls(dLateness)}>
              ({dLateness > 0 ? "+" : ""}
              {dLateness.toLocaleString()})
            </span>
          )}
        </span>
        {compare?.moved != null && (
          <span className="text-muted-foreground">moves {compare.moved.toLocaleString()} tasks</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={onCommit} disabled={committing}>
          {committing ? "Committing…" : "Commit draft"}
        </Button>
        <Button size="sm" variant="outline" onClick={onDiscard} disabled={discarding}>
          {discarding ? "Discarding…" : "Discard"}
        </Button>
      </div>
    </div>
  );
}

export function SchedulingGanttPage() {
  const current = useCurrentSchedule();
  const live = current.data ?? null;
  const draftQuery = useDraftSchedule();
  const draft = draftQuery.data ?? null;

  // Which schedule the board shows: live (committed) or the pending what-if draft.
  const [viewMode, setViewMode] = useState<"live" | "draft">("live");
  const viewingDraft = viewMode === "draft" && draft != null;
  const schedule = viewingDraft ? draft : live;
  // Stable Date objects for the horizon — a fresh `new Date()` each render was making
  // the Gantt's scroll-reset effect re-fire on every re-render (snapping scroll back
  // to the start). Memoize so the identity only changes when the schedule does.
  const horizonStart = useMemo(
    () => (schedule ? new Date(schedule.horizon_start) : null),
    [schedule?.horizon_start]
  );
  const horizonEnd = useMemo(
    () => (schedule ? new Date(schedule.horizon_end) : null),
    [schedule?.horizon_end]
  );

  const tasksQuery = useScheduledTasks(schedule?.id);
  const windowsQuery = useWorkingWindows(schedule?.id);
  const compareQuery = useCompareDraft(draft != null);
  const solve = useSolveSchedule();
  const solveDraft = useSolveDraft();
  const commitDraft = useCommitDraft();
  const discardDraft = useDiscardDraft();
  const dispatch = useDispatchSchedule();
  const pin = usePinTask();
  const move = useMoveTask();
  const moveBatch = useMoveBatch();
  const pinBatch = usePinBatch();

  // Zoom = fidelity. Ctrl/⌘ + wheel (what a trackpad pinch emits) zooms; so do the
  // toolbar buttons. Higher zoom widens the day columns so hourly detail is legible.
  const [zoom, setZoom] = useState(220);
  const [groupBy, setGroupBy] = useState<"machine" | "operator" | "product">("machine");
  const [search, setSearch] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailBatchId, setDetailBatchId] = useState<string | null>(null);
  // The "focused" job whose route chain draws peg lines. Set on bar click and kept
  // after the detail dialog closes, so the chain stays visible until cleared.
  const [focusId, setFocusId] = useState<string | null>(null);
  // Resource lanes are collapsed by default (all of a machine's tasks on ONE packed
  // row — they never overlap, so they fit). Expand a lane for one-task-per-row detail.
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggleExpand = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  const pageRef = useRef<HTMLDivElement>(null);
  // Smooth zoom: wheel/pinch and the toolbar buttons set a *target* zoom; a single rAF
  // tween eases the applied zoom toward it (~exponential approach). The applied value
  // drives the --gantt-column-width variable with NO CSS transition, so the column
  // width and the zoom-to-centre scroll adjustment move together on the same frame —
  // no easing lag, no anchor drift. Cheap now that the bars are decoupled from zoom:
  // a tween frame re-renders only this page, the provider, and the two px-based
  // overlays (shift bands, peg lines), never the ~200 bars.
  const targetZoom = useRef(220);
  const appliedZoom = useRef(220);
  const zoomRaf = useRef<number | null>(null);
  const tweenZoom = useCallback(() => {
    if (zoomRaf.current != null) return;
    const tick = () => {
      const target = targetZoom.current;
      const diff = target - appliedZoom.current;
      if (Math.abs(diff) <= 0.75) {
        appliedZoom.current = target;
        setZoom(target);
        zoomRaf.current = null;
        return;
      }
      appliedZoom.current += diff * 0.3; // ~exponential ease toward target
      setZoom(clampZoom(appliedZoom.current));
      zoomRaf.current = requestAnimationFrame(tick);
    };
    zoomRaf.current = requestAnimationFrame(tick);
  }, []);
  const nudgeZoom = useCallback(
    (factor: number) => {
      targetZoom.current = clampZoom(targetZoom.current * factor);
      tweenZoom();
    },
    [tweenZoom]
  );
  useEffect(() => {
    const el = pageRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return; // plain wheel scrolls; pinch/ctrl zooms
      e.preventDefault();
      const d = Math.max(-120, Math.min(120, e.deltaY));
      targetZoom.current = clampZoom(targetZoom.current * Math.exp(-d * 0.003));
      tweenZoom();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      el.removeEventListener("wheel", onWheel);
      if (zoomRaf.current != null) cancelAnimationFrame(zoomRaf.current);
    };
  }, [tweenZoom]);

  // Virtualization: only render bars whose time-range intersects the visible scroll
  // window (+ a buffer), so a 30-day, ~500-task board keeps only a few dozen bars in
  // the DOM. Track the timeline scroll container's scrollLeft/width, throttled to rAF.
  const [viewport, setViewport] = useState({ scrollLeft: 0, clientWidth: 4000 });
  useEffect(() => {
    const el = pageRef.current?.querySelector(".gantt") as HTMLElement | null;
    if (!el) return;
    // Read scroll/width from EVENTS (scroll + resize), never a per-frame rAF poll: the
    // poll read scrollLeft on every animation frame, and during a zoom (which dirties
    // layout each frame) that forced a synchronous reflow of the whole timeline per
    // frame — the jank the trace flagged. Scroll/resize handlers fire after layout has
    // settled, so their reads are clean. Programmatic scrolls (zoom-to-centre) still
    // emit scroll events, so the window keeps tracking.
    const read = () =>
      setViewport((v) => {
        const scrollLeft = el.scrollLeft;
        const clientWidth = el.clientWidth;
        return v.scrollLeft === scrollLeft && v.clientWidth === clientWidth
          ? v
          : { scrollLeft, clientWidth };
      });
    read(); // seed
    el.addEventListener("scroll", read, { passive: true });
    const ro = new ResizeObserver(read);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", read);
      ro.disconnect();
    };
    // Re-bind when the timeline (re)mounts — once tasks finish loading (dataUpdatedAt),
    // not just when the schedule id changes.
  }, [current.data?.id, draft?.id, viewingDraft, tasksQuery.dataUpdatedAt]);

  const allRows = (tasksQuery.data as { results?: Task[] } | undefined)?.results ?? [];
  const detailTask = allRows.find((r) => r.id === detailId) ?? null;
  const focusTask = allRows.find((r) => r.id === focusId) ?? null;

  // Visible day-fraction window for bar virtualization. Bars are positioned as a
  // fraction of a day-column from the horizon start, so we can filter by fraction
  // without touching the DOM. One-viewport buffer each side hides the recycling.
  const vizWindow = useMemo(() => {
    if (!schedule) return null;
    const dayPx = (720 * zoom) / 100; // hourly column width × zoom
    const buffer = viewport.clientWidth;
    return {
      origin: startOfDay(horizonStart!),
      startFrac: (viewport.scrollLeft - buffer) / dayPx,
      endFrac: (viewport.scrollLeft + viewport.clientWidth + buffer) / dayPx,
    };
  }, [schedule, zoom, viewport]);
  const inWindow = (f: { startAt: Date; endAt: Date | null }) => {
    if (!vizWindow) return true;
    const lf = differenceInMinutes(f.startAt, vizWindow.origin) / 1440;
    const rf = f.endAt ? differenceInMinutes(f.endAt, vizWindow.origin) / 1440 : lf + 0.02;
    return rf >= vizWindow.startFrac && lf <= vizWindow.endFrac;
  };

  // The focused job's steps, in time order — peg lines connect them.
  const pegChain = useMemo(() => {
    if (!focusTask) return [] as Task[];
    const k = unitKey(focusTask);
    if (!k) return [] as Task[];
    return allRows
      .filter((t) => unitKey(t) === k)
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  }, [focusTask, allRows]);
  const pegIds = useMemo(() => pegChain.map((t) => t.id), [pegChain]);

  const handleSelect = useCallback((id: string) => {
    if (isBatchId(id)) {
      setDetailBatchId(id); // a merged WO batch → batch dialog
      return;
    }
    setDetailId(id);
    setFocusId(id);
  }, []);

  // The per-lane load bar (busy-hours), shown in each resource header.
  const loadBar = (loadMinutes: number) =>
    loadMinutes > 0 ? (
      <span
        className="flex items-center gap-1.5"
        title={`${(loadMinutes / 60).toFixed(1)} h scheduled on this lane`}
      >
        <span className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
          <span
            className="block h-full rounded-full bg-sky-500"
            style={{ width: `${maxLoad ? (loadMinutes / maxLoad) * 100 : 0}%` }}
          />
        </span>
        <span className="tabular-nums">{(loadMinutes / 60).toFixed(1)}h</span>
      </span>
    ) : null;

  // Props shared by every rendered bar (drag, select, late-highlight).
  const barProps = (f: { id: string; is_late: boolean }) => ({
    onMove: onMoveTask,
    onSelect: handleSelect,
    cardClassName: f.is_late
      ? "ring-2 ring-inset ring-red-500 text-red-600 dark:text-red-400"
      : undefined,
  });

  // Collapsed-lane bars: a merged WO batch drags as a whole (re-anchor all its
  // parts); a single-task bar drags per-task.
  const laneBarProps = (f: { id: string; is_late: boolean }) => ({
    ...barProps(f),
    onMove: isBatchId(f.id) ? onMoveBatch : onMoveTask,
  });

  // Working windows → Date pairs; the Gantt shades the non-working complement.
  const shiftWindows = useMemo(
    () =>
      (
        (windowsQuery.data as { windows?: { start: string; end: string }[] } | undefined)
          ?.windows ?? []
      ).map((w) => ({ start: new Date(w.start), end: new Date(w.end) })),
    [windowsQuery.data]
  );

  // KPIs across the whole schedule (before any search filter).
  const kpis = useMemo(() => {
    let minStart = Infinity;
    let maxEnd = -Infinity;
    let uncovered = 0;
    const lateWos = new Set<string>();
    for (const t of allRows) {
      minStart = Math.min(minStart, new Date(t.start_time).getTime());
      maxEnd = Math.max(maxEnd, new Date(t.end_time).getTime());
      if (t.requires_operator && !t.operator_name) uncovered += 1;
      if (t.is_late) lateWos.add(t.work_order ?? t.id);
    }
    const makespanH =
      allRows.length && isFinite(minStart) ? (maxEnd - minStart) / 3_600_000 : 0;
    return { makespanH, uncovered, lateOrders: lateWos.size };
  }, [allRows]);

  // Text search filters which tasks show (across WO / unit / step / machine / operator).
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allRows;
    return allRows.filter((t) =>
      [t.work_order, t.part_erp, t.core_number, t.step_name, t.machine_name, t.operator_name, t.work_center]
        .some((v) => v?.toLowerCase().includes(q))
    );
  }, [allRows, search]);

  // Group the schedule by machine, by operator (people), or by product (part/core).
  const groupData = useMemo(() => {
    const key = (t: Task) =>
      groupBy === "operator"
        ? t.operator_name ?? "— Unassigned —"
        : groupBy === "product"
          ? t.part_erp ?? t.core_number ?? "—"
          : t.machine_name ?? "— Unassigned —";
    // Bars are labelled for the lane: a machine row shows the WORK ORDER it's
    // running, an operator row shows the WORK CENTER they're at, and the product row
    // (which IS a part) shows the step (+ machine).
    const featureName = (t: Task) => {
      const pin = `${t.is_pinned ? "📌 " : ""}${t.is_late ? "⏰ " : ""}`;
      const step = t.step_name ?? "";
      if (groupBy === "machine") {
        const wo = t.work_order ?? t.part_erp ?? t.core_number ?? "job";
        return `${pin}${wo} · ${step}`;
      }
      if (groupBy === "operator") {
        const wc = t.work_center ?? t.machine_name ?? "—";
        return `${pin}${wc} · ${step}`;
      }
      return `${pin}${step}${t.machine_name ? " @ " + t.machine_name : ""}`;
    };

    type Feat = GanttFeature & { is_pinned: boolean; is_late: boolean };
    const toFeature = (t: Task): Feat => {
      const zone = FENCE[t.fence_zone] ?? FENCE.liquid;
      return {
        id: t.id,
        name: featureName(t),
        startAt: new Date(t.start_time),
        endAt: new Date(t.end_time),
        status: { id: t.fence_zone, name: zone.name, color: zone.color },
        is_pinned: t.is_pinned,
        is_late: t.is_late,
      };
    };
    // A work order's batch key on a lane (parts of the same WO run contiguously).
    const woOf = (t: Task) => t.work_order ?? t.part_erp ?? t.core_number ?? "job";

    const meta = new Map<string, BatchMeta>();
    // Merge each lane's contiguous same-WO tasks into one batch bar (machine/people
    // views). A run of 1 stays a normal task bar. Product view never merges.
    const mergeBatches = (tasks: Task[]): Feat[] => {
      const sorted = [...tasks].sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );
      const out: Feat[] = [];
      let run: Task[] = [];
      const flush = () => {
        if (!run.length) return;
        if (run.length === 1) {
          out.push(toFeature(run[0]));
        } else {
          const first = run[0];
          const id = `batch:${first.id}`;
          const startAt = new Date(first.start_time);
          const endAt = new Date(
            run.reduce((m, t) => Math.max(m, new Date(t.end_time).getTime()), 0)
          );
          const anyLate = run.some((t) => t.is_late);
          const allPinned = run.every((t) => t.is_pinned);
          const zone = FENCE[first.fence_zone] ?? FENCE.liquid;
          out.push({
            id,
            name: `${allPinned ? "📌 " : ""}${anyLate ? "⏰ " : ""}${woOf(first)} · ${first.step_name ?? ""} ×${run.length}`,
            startAt,
            endAt,
            status: { id: first.fence_zone, name: zone.name, color: zone.color },
            is_pinned: allPinned,
            is_late: anyLate,
          });
          meta.set(id, {
            work_order: first.work_order,
            step_name: first.step_name,
            machine_name: first.machine_name,
            work_center: first.work_center,
            count: run.length,
            taskIds: run.map((t) => t.id),
            startAt,
            endAt,
            anyLate,
            allPinned,
          });
        }
        run = [];
      };
      for (const t of sorted) {
        if (run.length && woOf(t) !== woOf(run[run.length - 1])) flush();
        run.push(t);
      }
      flush();
      return out;
    };

    const byKey = new Map<string, Task[]>();
    for (const t of rows) {
      const k = key(t);
      (byKey.get(k) ?? byKey.set(k, []).get(k)!).push(t);
    }
    const list = [...byKey.entries()]
      .sort(([a], [b]) => (a.startsWith("—") ? 1 : b.startsWith("—") ? -1 : a.localeCompare(b)))
      .map(([name, tasks]) => ({
        machine: name,
        features: tasks.map(toFeature),                       // expanded: one bar per task
        batches: groupBy === "product" ? tasks.map(toFeature) // collapsed: merged WO batches
                                       : mergeBatches(tasks),
        loadMinutes: tasks.reduce(
          (s, t) => s + (new Date(t.end_time).getTime() - new Date(t.start_time).getTime()) / 60000,
          0
        ),
      }));
    return { list, batchMeta: meta };
  }, [rows, groupBy]);
  const groups = groupData.list;
  const batchMeta = groupData.batchMeta;
  const detailBatch = detailBatchId ? batchMeta.get(detailBatchId) ?? null : null;

  // Busiest lane, for scaling the per-lane load bars (relative utilization).
  const maxLoad = useMemo(
    () => groups.reduce((m, g) => Math.max(m, g.loadMinutes), 0),
    [groups]
  );

  // Drag-to-reschedule: pin the task at the dropped start. The server keeps its
  // duration and 422s (with a reason) if the drop breaks a local constraint; the
  // bar snaps back on refetch.
  const onMoveTask = useCallback((id: string, start: Date) => {
    move.mutate(
      { id, start_time: start.toISOString() },
      {
        onSuccess: () => toast.success("Task moved & pinned"),
        onError: (e: any) =>
          toast.error(e?.response?.data?.detail ?? "Couldn't move the task there"),
      }
    );
  }, [move]);

  // Drag a merged WO-batch bar: re-anchor all its parts to the drop time.
  const onMoveBatch = useCallback((id: string, start: Date) => {
    const meta = batchMeta.get(id);
    if (!meta) return;
    moveBatch.mutate(
      { task_ids: meta.taskIds, start_time: start.toISOString() },
      {
        onSuccess: (r: any) =>
          toast.success(`Moved ${r?.moved ?? meta.count} parts & pinned`),
        onError: (e: any) =>
          toast.error(e?.response?.data?.detail ?? "Couldn't move the batch there"),
      }
    );
  }, [moveBatch, batchMeta]);

  const toggleBatchPin = () => {
    if (!detailBatch) return;
    pinBatch.mutate(
      { task_ids: detailBatch.taskIds, is_pinned: !detailBatch.allPinned },
      {
        onSuccess: () =>
          toast.success(detailBatch.allPinned ? "Batch unpinned" : "Batch pinned"),
        onError: () => toast.error("Couldn't change the batch pin"),
      }
    );
  };

  const togglePin = (id: string) => {
    const t = rows.find((r) => r.id === id);
    if (!t) return;
    pin.mutate(
      { id, is_pinned: !t.is_pinned },
      {
        onSuccess: () => toast.success(t.is_pinned ? "Task unpinned" : "Task pinned"),
        onError: () => toast.error("Couldn't change the pin"),
      }
    );
  };

  return (
    <div ref={pageRef} className="flex h-full flex-col gap-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Production Schedule</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {schedule ? (
              <>
                {viewingDraft && (
                  <Badge className="border-transparent bg-amber-500 text-white hover:bg-amber-500">
                    DRAFT (what-if)
                  </Badge>
                )}
                <Badge variant="secondary">{schedule.solver_status}</Badge>
                <span>{schedule.task_count} tasks</span>
                <span>· makespan {kpis.makespanH.toFixed(1)} h</span>
                <span
                  title="Priority-weighted lateness (Σ part late-minutes × the WO's priority penalty). Not a monetary value — the solver has no fiscal data."
                >
                  · lateness{" "}
                  {schedule.weighted_lateness > 0
                    ? `${schedule.weighted_lateness.toLocaleString()} (priority-wtd)`
                    : "none"}
                </span>
                <span>· solved in {schedule.solve_time_ms} ms</span>
                {kpis.uncovered > 0 && (
                  <Badge variant="destructive">{kpis.uncovered} uncovered</Badge>
                )}
                {kpis.lateOrders > 0 && (
                  <Badge variant="destructive">⏰ {kpis.lateOrders} late order(s)</Badge>
                )}
                {schedule.is_stale && <Badge variant="outline">stale — re-solve</Badge>}
              </>
            ) : (
              <span>No active schedule yet — run Solve.</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative mr-1">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search WO / part / step / machine / operator…"
              className="h-8 w-64 pl-8"
            />
          </div>
          {focusTask && (
            <button
              type="button"
              onClick={() => setFocusId(null)}
              className="mr-1 flex h-8 items-center gap-1 rounded-md border border-sky-500/40 bg-sky-500/10 px-2 text-xs text-sky-600 hover:bg-sky-500/20 dark:text-sky-400"
              title="Clear the focused job (peg lines)"
            >
              ◉ {focusTask.part_erp ?? focusTask.core_number ?? "job"}
              <span className="text-muted-foreground">✕</span>
            </button>
          )}
          <div className="mr-1 flex items-center rounded-md border p-0.5">
            {([
              ["machine", "Machines"],
              ["operator", "People"],
              ["product", "Product"],
            ] as const).map(([mode, label]) => (
              <Button
                key={mode}
                variant={groupBy === mode ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => setGroupBy(mode)}
              >
                {label}
              </Button>
            ))}
          </div>
          <div className="mr-1 flex items-center gap-1 rounded-md border px-1" title="Ctrl/⌘ + scroll, or pinch, to zoom">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => nudgeZoom(0.8)}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="w-12 text-center text-xs tabular-nums text-muted-foreground">{zoom}%</span>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => nudgeZoom(1.25)}>
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
          {draft && (
            <div className="mr-1 flex items-center rounded-md border p-0.5">
              {(["live", "draft"] as const).map((m) => (
                <Button
                  key={m}
                  variant={viewMode === m ? "secondary" : "ghost"}
                  size="sm"
                  className="h-7 px-2 text-xs capitalize"
                  onClick={() => setViewMode(m)}
                >
                  {m}
                </Button>
              ))}
            </div>
          )}
          <Button onClick={solve.run} disabled={solve.isRunning}>
            {solve.isRunning ? "Solving…" : "Solve"}
          </Button>
          <Button
            variant="outline"
            onClick={solveDraft.run}
            disabled={solveDraft.isRunning}
            title="Explore a what-if without touching the live schedule"
          >
            {solveDraft.isRunning ? "Solving…" : "What-if"}
          </Button>
          <Button variant="secondary" onClick={dispatch.run} disabled={dispatch.isRunning || !live}>
            {dispatch.isRunning ? "Dispatching…" : "Dispatch"}
          </Button>
        </div>
      </header>

      {draft && (
        <DraftCompareBar
          compare={compareQuery.data as CompareResult | undefined}
          committing={commitDraft.isPending}
          discarding={discardDraft.isPending}
          onCommit={() =>
            commitDraft.mutate(undefined, {
              onSuccess: () => {
                setViewMode("live");
                toast.success("Draft committed — now the live schedule");
              },
              onError: () => toast.error("Couldn't commit the draft"),
            })
          }
          onDiscard={() =>
            discardDraft.mutate(undefined, {
              onSuccess: () => {
                setViewMode("live");
                toast.success("Draft discarded");
              },
              onError: () => toast.error("Couldn't discard the draft"),
            })
          }
        />
      )}

      {schedule && schedule.relaxed_pin_count > 0 && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
          ⚠ {schedule.relaxed_pin_count} frozen task(s) had to move — the world changed under
          the pinned plan. Review before committing.
        </div>
      )}

      {!schedule ? null : tasksQuery.isLoading ? (
        <p className="text-muted-foreground">Loading tasks…</p>
      ) : rows.length === 0 ? (
        <p className="text-muted-foreground">This schedule has no tasks.</p>
      ) : (
        <GanttProvider
          range="hourly"
          zoom={zoom}
          boundStart={horizonStart!}
          boundEnd={horizonEnd!}
          className="min-h-0 flex-1 rounded-lg border"
        >
          <GanttSidebar>
            {groups.map((g) => {
              const isExpanded = expanded.has(g.machine);
              return (
                <div key={g.machine}>
                  {/* Resource header row — click to expand into one-task-per-row detail. */}
                  <button
                    type="button"
                    onClick={() => toggleExpand(g.machine)}
                    className="flex w-full items-center gap-2 p-2.5 text-left font-medium text-muted-foreground text-xs hover:bg-secondary/50"
                    style={{ height: "var(--gantt-row-height)" }}
                    title={isExpanded ? "Collapse lane" : "Expand lane"}
                  >
                    <ChevronRight
                      className={`h-3.5 w-3.5 shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                    />
                    <span className="flex-1 truncate">{g.machine}</span>
                    {loadBar(g.loadMinutes)}
                  </button>
                  {isExpanded && (
                    <div className="divide-y divide-border/50">
                      {g.features.map((f) => (
                        // Row click scrolls to the task (built-in); it does NOT pin or
                        // open the detail — click the bar for that.
                        <GanttSidebarItem key={f.id} feature={f} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </GanttSidebar>
          <GanttTimeline>
            <GanttHeader />
            {shiftWindows.length > 0 && (
              <GanttShiftBands
                windows={shiftWindows}
                rangeStart={horizonStart!}
                rangeEnd={horizonEnd!}
              />
            )}
            <GanttFeatureList>
              {groups.map((g) =>
                expanded.has(g.machine) ? (
                  <GanttFeatureListGroup key={g.machine}>
                    {g.features.map((f) => (
                      <GanttFeatureItem key={f.id} {...f} {...barProps(f)} />
                    ))}
                  </GanttFeatureListGroup>
                ) : (
                  // Collapsed: all of this resource's bars on ONE packed lane row.
                  // They never overlap (machine/operator/part runs one thing at a time).
                  <div
                    key={g.machine}
                    className="relative w-max min-w-full py-0.5"
                    style={{ height: "var(--gantt-row-height)" }}
                  >
                    {g.batches.filter(inWindow).map((f) => (
                      <GanttFeatureItem key={f.id} {...f} {...laneBarProps(f)} bare />
                    ))}
                  </div>
                )
              )}
            </GanttFeatureList>
            <GanttPegLines ids={pegIds} revision={tasksQuery.dataUpdatedAt} />
            <GanttToday />
          </GanttTimeline>
        </GanttProvider>
      )}

      <Dialog open={detailTask != null} onOpenChange={(o) => !o && setDetailId(null)}>
        <DialogContent className="sm:max-w-md">
          {detailTask && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span>
                    {detailTask.part_erp ?? detailTask.core_number ?? "Task"} ·{" "}
                    {detailTask.step_name}
                  </span>
                  {detailTask.is_late && <Badge variant="destructive">⏰ Late</Badge>}
                </DialogTitle>
              </DialogHeader>
              <dl className="grid grid-cols-[7rem_1fr] gap-y-1.5 text-sm">
                <dt className="text-muted-foreground">Work order</dt>
                <dd>{detailTask.work_order ?? "—"}</dd>
                <dt className="text-muted-foreground">Due date</dt>
                <dd className={detailTask.is_late ? "text-red-600 dark:text-red-400" : undefined}>
                  {detailTask.due_date ?? "— none —"}
                </dd>
                <dt className="text-muted-foreground">Machine</dt>
                <dd>{detailTask.machine_name ?? "— none —"}</dd>
                <dt className="text-muted-foreground">Work center</dt>
                <dd>{detailTask.work_center ?? "—"}</dd>
                <dt className="text-muted-foreground">Operator</dt>
                <dd>
                  {detailTask.operator_name ??
                    (detailTask.requires_operator ? "⚠ uncovered" : "— unattended —")}
                </dd>
                <dt className="text-muted-foreground">Start</dt>
                <dd>{new Date(detailTask.start_time).toLocaleString()}</dd>
                <dt className="text-muted-foreground">End</dt>
                <dd>{new Date(detailTask.end_time).toLocaleString()}</dd>
                <dt className="text-muted-foreground">Fence zone</dt>
                <dd className="capitalize">{detailTask.fence_zone}</dd>
              </dl>
              <DialogFooter>
                <Button
                  variant={detailTask.is_pinned ? "secondary" : "default"}
                  onClick={() => togglePin(detailTask.id)}
                  disabled={pin.isPending}
                >
                  {detailTask.is_pinned ? (
                    <>
                      <PinOff className="mr-1 h-4 w-4" /> Unpin
                    </>
                  ) : (
                    <>
                      <Pin className="mr-1 h-4 w-4" /> Pin
                    </>
                  )}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Merged work-order batch (a WO's parts at one operation on this lane). */}
      <Dialog open={detailBatch != null} onOpenChange={(o) => !o && setDetailBatchId(null)}>
        <DialogContent className="sm:max-w-md">
          {detailBatch && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span>
                    {detailBatch.work_order ?? "Work order"} · {detailBatch.step_name}
                  </span>
                  <Badge variant="secondary">{detailBatch.count} parts</Badge>
                  {detailBatch.anyLate && <Badge variant="destructive">⏰ Late</Badge>}
                </DialogTitle>
              </DialogHeader>
              <dl className="grid grid-cols-[7rem_1fr] gap-y-1.5 text-sm">
                <dt className="text-muted-foreground">Operation</dt>
                <dd>{detailBatch.step_name ?? "—"}</dd>
                <dt className="text-muted-foreground">Machine</dt>
                <dd>{detailBatch.machine_name ?? "— none —"}</dd>
                <dt className="text-muted-foreground">Work center</dt>
                <dd>{detailBatch.work_center ?? "—"}</dd>
                <dt className="text-muted-foreground">Parts</dt>
                <dd>{detailBatch.count} (pinned: {detailBatch.allPinned ? "all" : "some/none"})</dd>
                <dt className="text-muted-foreground">Batch start</dt>
                <dd>{detailBatch.startAt.toLocaleString()}</dd>
                <dt className="text-muted-foreground">Batch end</dt>
                <dd>{detailBatch.endAt.toLocaleString()}</dd>
              </dl>
              <p className="text-xs text-muted-foreground">
                Drag the batch bar to re-anchor all {detailBatch.count} parts; expand the
                lane (▸) to move or pin individual parts.
              </p>
              <DialogFooter>
                <Button
                  variant={detailBatch.allPinned ? "secondary" : "default"}
                  onClick={toggleBatchPin}
                  disabled={pinBatch.isPending}
                >
                  {detailBatch.allPinned ? (
                    <>
                      <PinOff className="mr-1 h-4 w-4" /> Unpin all
                    </>
                  ) : (
                    <>
                      <Pin className="mr-1 h-4 w-4" /> Pin all
                    </>
                  )}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default SchedulingGanttPage;
