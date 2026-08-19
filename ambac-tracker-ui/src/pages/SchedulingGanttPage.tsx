// Production schedule Gantt — reads the active CP-SAT schedule and renders it,
// grouped by machine, with solve / dispatch actions and pin toggling.
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ZoomIn, ZoomOut } from "lucide-react";
import {
  GanttProvider,
  GanttSidebar,
  GanttSidebarGroup,
  GanttSidebarItem,
  GanttTimeline,
  GanttHeader,
  GanttFeatureList,
  GanttFeatureListGroup,
  GanttFeatureItem,
  GanttToday,
  type GanttFeature,
} from "@/components/kibo-ui/gantt";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useCurrentSchedule,
  useScheduledTasks,
  useSolveSchedule,
  useDispatchSchedule,
  usePinTask,
} from "@/hooks/useScheduling";

const FENCE = {
  frozen: { name: "Frozen", color: "#ef4444" },
  slushy: { name: "Slushy", color: "#f59e0b" },
  liquid: { name: "Liquid", color: "#22c55e" },
} as const;

type Task = {
  id: string;
  part_erp: string | null;
  core_number: string | null;
  step_name: string | null;
  machine_name: string | null;
  operator_name: string | null;
  start_time: string;
  end_time: string;
  is_pinned: boolean;
  fence_zone: keyof typeof FENCE;
};

export function SchedulingGanttPage() {
  const current = useCurrentSchedule();
  const schedule = current.data ?? null;
  const tasksQuery = useScheduledTasks(schedule?.id);
  const solve = useSolveSchedule();
  const dispatch = useDispatchSchedule();
  const pin = usePinTask();

  // Zoom = fidelity. Ctrl/⌘ + wheel (what a trackpad pinch emits) zooms; so do the
  // toolbar buttons. Higher zoom widens the day columns so hourly detail is legible.
  const [zoom, setZoom] = useState(220);
  const pageRef = useRef<HTMLDivElement>(null);
  const clampZoom = (z: number) => Math.min(1500, Math.max(30, Math.round(z)));
  useEffect(() => {
    const el = pageRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return; // plain wheel scrolls; pinch/ctrl zooms
      e.preventDefault();
      setZoom((z) => clampZoom(z * (e.deltaY < 0 ? 1.12 : 0.89)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const rows = (tasksQuery.data as { results?: Task[] } | undefined)?.results ?? [];

  // Group tasks by machine (Unassigned last) → GanttFeatures.
  const groups = useMemo(() => {
    const byMachine = new Map<string, (GanttFeature & { is_pinned: boolean })[]>();
    for (const t of rows) {
      const machine = t.machine_name ?? "— Unassigned —";
      const unit = t.part_erp ?? t.core_number ?? "task";
      const zone = FENCE[t.fence_zone] ?? FENCE.liquid;
      const feature: GanttFeature & { is_pinned: boolean } = {
        id: t.id,
        name: `${t.is_pinned ? "📌 " : ""}${unit} · ${t.step_name ?? ""}`,
        startAt: new Date(t.start_time),
        endAt: new Date(t.end_time),
        status: { id: t.fence_zone, name: zone.name, color: zone.color },
        is_pinned: t.is_pinned,
      };
      (byMachine.get(machine) ?? byMachine.set(machine, []).get(machine)!).push(feature);
    }
    return [...byMachine.entries()]
      .sort(([a], [b]) => (a.startsWith("—") ? 1 : b.startsWith("—") ? -1 : a.localeCompare(b)))
      .map(([machine, features]) => ({ machine, features }));
  }, [rows]);

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

  const runSolve = () =>
    solve.mutate(undefined, {
      onSuccess: () => toast.success("Schedule solved"),
      onError: () => toast.error("Solve failed — do you have the Planner permission?"),
    });
  const runDispatch = () =>
    dispatch.mutate(undefined, {
      onSuccess: (r: any) =>
        toast.success(`Dispatched: ${r?.covered ?? 0}/${r?.attended ?? 0} attended tasks covered`),
      onError: () => toast.error("Dispatch failed"),
    });

  return (
    <div ref={pageRef} className="flex h-full flex-col gap-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Production Schedule</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {schedule ? (
              <>
                <Badge variant="secondary">{schedule.solver_status}</Badge>
                <span>{schedule.task_count} tasks</span>
                <span>· solved in {schedule.solve_time_ms} ms</span>
                {schedule.is_stale && <Badge variant="outline">stale — re-solve</Badge>}
              </>
            ) : (
              <span>No active schedule yet — run Solve.</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="mr-1 flex items-center gap-1 rounded-md border px-1" title="Ctrl/⌘ + scroll, or pinch, to zoom">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => clampZoom(z * 0.8))}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="w-12 text-center text-xs tabular-nums text-muted-foreground">{zoom}%</span>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((z) => clampZoom(z * 1.25))}>
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={runSolve} disabled={solve.isPending}>
            {solve.isPending ? "Solving…" : "Solve"}
          </Button>
          <Button variant="secondary" onClick={runDispatch} disabled={dispatch.isPending || !schedule}>
            {dispatch.isPending ? "Dispatching…" : "Dispatch"}
          </Button>
        </div>
      </header>

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
        <GanttProvider range="hourly" zoom={zoom} className="min-h-0 flex-1 rounded-lg border">
          <GanttSidebar>
            {groups.map((g) => (
              <GanttSidebarGroup key={g.machine} name={g.machine}>
                {g.features.map((f) => (
                  <GanttSidebarItem key={f.id} feature={f} onSelectItem={togglePin} />
                ))}
              </GanttSidebarGroup>
            ))}
          </GanttSidebar>
          <GanttTimeline>
            <GanttHeader />
            <GanttFeatureList>
              {groups.map((g) => (
                <GanttFeatureListGroup key={g.machine}>
                  {g.features.map((f) => (
                    <GanttFeatureItem key={f.id} {...f} onMove={undefined} />
                  ))}
                </GanttFeatureListGroup>
              ))}
            </GanttFeatureList>
            <GanttToday />
          </GanttTimeline>
        </GanttProvider>
      )}
    </div>
  );
}

export default SchedulingGanttPage;
