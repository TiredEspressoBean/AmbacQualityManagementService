// Hooks for the CP-SAT scheduling API (solve / dispatch / read / pin).
import { useEffect, useRef, useState } from "react";
import { queryOptions, skipToken, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { underRoot } from "@/lib/query-filters";

/** Cache-key roots this module owns. Prefix invalidations match against these
 *  rather than repeating the string, so a rename lands in one place. Keys
 *  themselves are declared by the `queryOptions()` factories below — that is
 *  the one place a full key is spelled. */
const ROOT = {
  schedule: "schedule",
  scheduledTasks: "scheduled-tasks",
  workOrder: "work-order",
  planning: "planning",
  stagingList: "staging-list",
  shifts: "shifts",
  fixtures: "fixtures",
} as const;

/** The active schedule's run metadata (null when none has been solved yet). */
export const currentScheduleOptions = () =>
  queryOptions({
    queryKey: ["schedule", "current"],
    queryFn: async () => {
      try {
        return await api.api_Schedules_current_retrieve();
      } catch (e: any) {
        if (e?.response?.status === 404) return null; // no active schedule yet
        throw e;
      }
    },
  });

export function useCurrentSchedule() {
  return useQuery(currentScheduleOptions());
}

/** Scheduled tasks (Gantt rows) for a schedule. */
export const scheduledTasksOptions = (scheduleId?: string) =>
  queryOptions({
    queryKey: ["scheduled-tasks", scheduleId],
    enabled: !!scheduleId,
    queryFn: () =>
      // Fetch the whole schedule (default page size is 25) so every machine/operator
      // lane is populated, not just the earliest 25 tasks.
      api.api_ScheduledTasks_list({
        queries: { schedule: scheduleId, ordering: "start_time", limit: 2000 },
      }),
  });

export function useScheduledTasks(scheduleId?: string) {
  return useQuery(scheduledTasksOptions(scheduleId));
}

/** Re-anchor a work-order batch (many parts at one op) to a new start. 422s with a
 * `detail` reason if any part breaks a local constraint. */
export function useMoveBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, start_time }: { task_ids: string[]; start_time: string }) =>
      api.api_ScheduledTasks_move_batch_create({ task_ids, start_time }),
    onSettled: () => invalidateSchedule(qc),
    // The drag handler toasts the reason and rolls the bars back.
    meta: { suppressGlobalError: true },
  });
}

/** Pin / unpin every part of a work-order batch. */
export function usePinBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, is_pinned }: { task_ids: string[]; is_pinned: boolean }) =>
      api.api_ScheduledTasks_pin_batch_create({ task_ids, is_pinned }),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Tenant working windows over the active schedule's horizon (for shift shading). */
export const workingWindowsOptions = (scheduleId?: string) =>
  queryOptions({
    queryKey: ["schedule", "working-windows", scheduleId],
    enabled: !!scheduleId,
    queryFn: () => api.api_Schedules_working_windows_retrieve(),
  });

export function useWorkingWindows(scheduleId?: string) {
  return useQuery(workingWindowsOptions(scheduleId));
}

function invalidateSchedule(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries(underRoot(ROOT.schedule));
  qc.invalidateQueries(underRoot(ROOT.scheduledTasks));
}

/** Poll state for one background solve/dispatch task. */
export const solveStatusOptions = (taskId: string | null) =>
  queryOptions({
    queryKey: ["solve-status", taskId],
    queryFn: taskId
      ? () => api.api_Schedules_solve_status_retrieve({ queries: { task_id: taskId } })
      : skipToken,
    // Poll while the task is queued/running; stop once it's terminal.
    refetchInterval: (q) => {
      const s = q.state.data?.state;
      return s === "SUCCESS" || s === "FAILURE" ? false : 1500;
    },
  });

/** Kick off a background scheduling task (solve / dispatch), then poll `solve_status`
 * until it finishes and refresh the schedule. Returns `{ run, isRunning }` — the task
 * runs on the server for as long as it needs, so the UI stays responsive. */
function useAsyncScheduleTask(
  trigger: () => Promise<{ task_id: string }>,
  labels: { done: (result: any) => string; verb: string },
  onDone?: (result: any) => void
) {
  const qc = useQueryClient();
  const [taskId, setTaskId] = useState<string | null>(null);
  const labelsRef = useRef(labels);
  labelsRef.current = labels;
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const start = useMutation({
    mutationFn: trigger,
    onSuccess: (r: any) => setTaskId(r.task_id),
    onError: () => toast.error(`Couldn't start ${labelsRef.current.verb}`),
    // Own message is specific; the global handler would add a vaguer duplicate.
    meta: { suppressGlobalError: true },
  });

  const status = useQuery(solveStatusOptions(taskId));

  useEffect(() => {
    const d = status.data;
    if (!d || !taskId) return;
    if (d.state === "SUCCESS") {
      invalidateSchedule(qc);
      toast.success(labelsRef.current.done(d.result));
      setTaskId(null);
      onDoneRef.current?.(d.result);
    } else if (d.state === "FAILURE") {
      toast.error(d.detail ?? `${labelsRef.current.verb} failed`);
      setTaskId(null);
    }
  }, [status.data, taskId, qc]);

  return { run: () => start.mutate(), isRunning: start.isPending || !!taskId };
}

/** Run the Layer-1 solver in the background (supersedes the active schedule). */
export function useSolveSchedule() {
  return useAsyncScheduleTask(
    () => api.api_Schedules_solve_create(undefined) as Promise<{ task_id: string }>,
    { verb: "the solve", done: (r) => `Schedule solved (${r?.solver_status ?? "done"})` }
  );
}

/** Run a what-if solve in the background — produces a draft, live untouched.
 * `onReady` fires when the draft is solved (used to auto-switch the board to the
 * draft view, so the what-if shows itself instead of hiding behind a toggle). */
export function useSolveDraft(onReady?: () => void) {
  return useAsyncScheduleTask(
    () => api.api_Schedules_solve_draft_create(undefined) as Promise<{ task_id: string }>,
    { verb: "the what-if", done: () => "What-if draft ready — showing it now" },
    onReady
  );
}

/** The pending what-if draft (null when none). */
export const draftScheduleOptions = () =>
  queryOptions({
    queryKey: ["schedule", "draft"],
    queryFn: async () => {
      try {
        return await api.api_Schedules_draft_retrieve();
      } catch (e: any) {
        if (e?.response?.status === 404) return null; // no draft pending
        throw e;
      }
    },
  });

export function useDraftSchedule() {
  return useQuery(draftScheduleOptions());
}

/** Live-vs-draft comparison (summaries + moved-task count); only when a draft exists. */
export const compareDraftOptions = (enabled: boolean) =>
  queryOptions({
    queryKey: ["schedule", "compare"],
    enabled,
    queryFn: () => api.api_Schedules_compare_retrieve(),
  });

export function useCompareDraft(enabled: boolean) {
  return useQuery(compareDraftOptions(enabled));
}

/** Promote the draft to the live schedule. */
export function useCommitDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_commit_create(undefined),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Throw the draft away, leaving live untouched. */
export function useDiscardDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_discard_create(undefined),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Assign operators to the active schedule (Layer 2) in the background. */
export function useDispatchSchedule() {
  return useAsyncScheduleTask(
    () => api.api_Schedules_dispatch_create(undefined) as Promise<{ task_id: string }>,
    {
      verb: "dispatch",
      done: (r) =>
        r?.covered != null
          ? `Dispatched: ${r.covered}/${r.attended} attended tasks covered`
          : "Dispatch complete",
    }
  );
}

export type ActiveRun = {
  running: boolean;
  stale?: boolean;
  kind?: "solve" | "draft" | "dispatch";
  task_id?: string;
  /** PENDING = queued and waiting for a worker; STARTED = a worker has it. */
  state?: string;
  seconds_elapsed?: number;
  seconds_remaining?: number;
  limit_seconds?: number;
  last_state?: string;
};

/** What this TENANT has in flight — not just what this tab started.
 *
 *  The task id used to live only in the requesting tab's state, so a colleague looking
 *  at the same board saw it not changing and no reason why. Polling without a task id
 *  answers for the tenant, so every client shows the same thing.
 *
 *  Polls quickly while something is running and slowly otherwise, so another planner's
 *  solve shows up here within a few seconds without hammering the endpoint all day. */
export const activeRunOptions = () =>
  queryOptions({
    queryKey: ["schedule", "active-run"],
    queryFn: () => api.api_Schedules_solve_status_retrieve() as Promise<ActiveRun>,
    refetchInterval: (q) => ((q.state.data as ActiveRun)?.running ? 2000 : 10000),
    refetchOnWindowFocus: true,
  });

export function useActiveRun() {
  return useQuery(activeRunOptions());
}

/** The tenant's solver knobs (time limit, fences, penalties, labor model). */
export const optimizationConfigOptions = () =>
  queryOptions({
    queryKey: ["schedule", "config"],
    queryFn: () => api.api_Schedules_config_retrieve(),
  });

export function useOptimizationConfig() {
  return useQuery(optimizationConfigOptions());
}

/** Update the tenant's solver knobs (partial). */
export function useUpdateOptimizationConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Record<string, unknown>) =>
      api.api_Schedules_config_partial_update(patch),
    onSuccess: () => {
      qc.invalidateQueries(optimizationConfigOptions());
      toast.success("Solver settings saved");
    },
    onError: () => toast.error("Couldn't save solver settings"),
  });
}

/** Merge selected tasks into one lot (one ×N cell) or break them apart into separate
 * bars. `merge=false` splits; `merge=true` folds back together. */
export function useBatchMembership() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, merge }: { task_ids: string[]; merge: boolean }) =>
      api.api_ScheduledTasks_batch_membership_create({ task_ids, merge }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      toast.success(
        r?.merged
          ? `Merged ${r.changed} part(s) into one batch — re-solve to group them`
          : `Broke apart ${r.changed} part(s) — re-solve to separate them`
      );
    },
    onError: () => toast.error("Couldn't change batching"),
  });
}

/** Fetch a work order (for the edit dialog's current values). */
export const workOrderOptions = (id: string | null) =>
  queryOptions({
    queryKey: ["work-order", id],
    queryFn: id ? () => api.api_WorkOrders_retrieve({ params: { id } }) : skipToken,
  });

export function useWorkOrder(id: string | null) {
  return useQuery(workOrderOptions(id));
}

/** Operator shop-hours over a date range — on-shift (attendance) + direct (job) hours,
 *  from TimeEntry, scoped to shop-floor operators. */
export type OperatorHoursRow = {
  user_id: number; name: string; on_shift_hours: number; direct_hours: number;
};
export const operatorHoursOptions = (start: string, end: string) =>
  queryOptions({
    queryKey: ["operator-hours", start, end],
    queryFn: async () =>
      ((await api.api_Schedules_operator_hours_retrieve({
        queries: { start, end },
      })) as { rows?: OperatorHoursRow[] }).rows ?? [],
  });

export function useOperatorHours(start: string, end: string) {
  return useQuery(operatorHoursOptions(start, end));
}

/** Sourcing & production requirements — what open demand needs bought (source) or built
 *  (produce), plus tooling not on hand, with lead-time-driven order-by dates. */
export type SourceRow = {
  material: string; qty_short: number; need_by: string; lead_time_days: number | null;
  order_by: string | null; incoming_date: string | null;
};
export type ProduceRow = {
  work_order: string; component: string; qty: number; need_by: string; status: string;
};
export type ToolingRow = {
  fixture: string; kind: string; need_by: string; lead_time_days: number | null;
  order_by: string | null;
};
export const requirementsOptions = () =>
  queryOptions({
    queryKey: ["schedule", "requirements"],
    queryFn: () =>
      api.api_Schedules_requirements_retrieve() as Promise<{
        source: SourceRow[]; produce: ProduceRow[]; tooling: ToolingRow[];
      }>,
  });

export function useRequirements() {
  return useQuery(requirementsOptions());
}

/* --- Rough-cut capacity planning ------------------------------------------
 * The coarse layer above CP-SAT: monthly capacity-vs-load arithmetic over a horizon
 * far past what the solver plans in detail, and the "could we take this order?" quote
 * built on it. */

export type CapacityBucket = {
  bucket: string; capacity_hours: number; load_hours: number;
  utilization: number | null;
};
/** A back-scheduled release date: when this order has to START to hit its due date.
 *  `is_estimate` marks a date RCCP derived (due date minus lead time) rather than one a
 *  planner set — RCCP suggests, it never writes `expected_start`. */
export type PlannedRelease = {
  work_order_id: string;
  erp_id: string;
  planned_start: string;
  due_date: string | null;
  overdue: boolean;
  is_estimate: boolean;
  released: boolean;
};
export type CapacityLoad = {
  buckets: string[];
  labor: { name: string; crew_size: number; series: CapacityBucket[] };
  work_centers: {
    id: string; name: string; series: CapacityBucket[];
    /** Planner-declared "worth watching". Marks the row when unfiltered, and is what
     *  `critical_only` filters on. Independent of the release-pacing bottleneck flag. */
    is_critical: boolean;
  }[];
  /** Certification-limited labour, one row per distinct qualified crew carrying gated
   *  work. The aggregate `labor` lane asks "enough people"; these ask "enough of the
   *  RIGHT people" — pools can overlap, so a row reads as the binding constraint for
   *  its own work rather than a claim every pool is satisfiable at once. */
  labor_pools: { name: string; qualified: number; series: CapacityBucket[] }[];
  /** Work centres that exist, before any filter — so a narrowed lane can say what it
   *  is hiding instead of looking like a two-centre shop. */
  work_center_total: number;
  critical_only: boolean;
  planned_releases: PlannedRelease[];
  /** Orders with an operation nobody has timed. Such a step costs zero hours and zero
   *  lead days, so it reads as free rather than unknown — their load and release dates
   *  are a floor. */
  untimed_orders: { erp_id: string; step_count: number }[];
  /** Material demand on the same buckets. Separate shape from the capacity lanes: a
   *  material has a balance rather than an hourly capacity, so the cell carries what is
   *  LEFT rather than a ratio — a percentage of a stock level reads as a consumption
   *  rate on a row where it is nothing of the sort. */
  materials: {
    id: string;
    name: string;
    series: {
      bucket: string;
      demand: number;
      cumulative_demand: number;
      available: number;
      /** Stock left after everything committed through this bucket. Negative = short. */
      remaining_cover: number;
      short: boolean;
    }[];
  }[];
};
/** `criticalOnly` narrows the work-centre lane to the centres a planner flagged.
 *  It is part of the query key because it changes the response, but NOT part of the
 *  arithmetic: a row kept by the filter carries the same numbers it carries unfiltered
 *  (the backend computes load over every centre either way). */
export const capacityLoadOptions = (months = 12, criticalOnly = false) =>
  queryOptions({
    queryKey: ["planning", "capacity-load", months, criticalOnly],
    queryFn: () =>
      api.api_Schedules_capacity_load_retrieve({
        queries: { months, critical_only: criticalOnly },
      }) as Promise<CapacityLoad>,
  });

export function useCapacityLoad(months = 12, criticalOnly = false) {
  return useQuery(capacityLoadOptions(months, criticalOnly));
}

export type CtpBinding = {
  resource: string; need: number; free_through_target: number;
};
export type CtpQuote = {
  feasible: boolean;
  reason?: string;
  target_bucket?: string;
  binding_resources?: CtpBinding[];
  earliest_feasible_bucket?: string | null;
  quantity?: number;
  work_content_hours?: Record<string, number>;
};
/** Quote an order against remaining capacity. Disabled until every input is set —
 *  a half-filled form must not fire a request that can only answer 400. */
export const capableToPromiseOptions = (
  args: { part_type: string; quantity: number; target_date: string; months?: number } | null
) =>
  queryOptions({
    queryKey: ["planning", "ctp", args],
    // A half-filled form must not fire a request that can only answer 400.
    queryFn:
      args && args.part_type && args.quantity > 0 && args.target_date
        ? () =>
            api.api_Schedules_capable_to_promise_retrieve({
              queries: args,
            }) as Promise<CtpQuote>
        : skipToken,
  });

export function useCapableToPromise(
  args: { part_type: string; quantity: number; target_date: string; months?: number } | null
) {
  return useQuery(capableToPromiseOptions(args));
}

/* --- Staging pick list ----------------------------------------------------
 * What to put at each bench before the operator arrives. Reads the SCHEDULE, so it
 * only says anything once a solve has run. */

export type StagingLot = {
  lot_id: string; lot_number: string; storage_location: string;
  expiration_date: string | null; take: number;
};
export type StagingMaterial = {
  material_id: string;
  /** Whether `material_id` is a raw Material or a purchased PartTypes. The two id
   *  spaces can collide, so this rides along rather than being inferred server-side.
   *  Absent on older responses, which were Material-only. */
  kind?: "MATERIAL" | "PART_TYPE";
  material: string; needed: number; on_hand: number; short: number;
  optional: boolean;
  /** What was actually recorded as pulled. Null = nobody has confirmed this line yet,
   *  so consumption will fall back to FEFO and assert the plan rather than the fact. */
  picked_qty: number | null;
  picked_lots: { lot_id: string; lot_number: string; qty: number }[];
  /** Recorded lots differ from the planned ones — the named lot was empty, short, or
   *  already gone. The case worth seeing. */
  deviated: boolean;
  /** The lots consumption WILL draw (FEFO). Pull these so the traceability record
   *  matches what physically went into the unit. */
  lots: StagingLot[];
};
export type StagingJob = {
  work_order_id: string; erp_id: string; part_type: string | null;
  step_id: string; step_name: string;
  work_center_id: string; work_center: string;
  starts_at: string; units: number; machine: string | null;
  materials: StagingMaterial[]; fixtures: string[]; short_count: number;
  /** Kept per (work order, step), so it survives a re-solve — the solver replaces
   *  every ScheduledTask row and staging must not vanish with them. */
  staged_at: string | null; staged_by: string | null; staging_note: string;
};
export type StagingStation = {
  work_center_id: string; name: string; jobs: StagingJob[];
  short_count: number; staged_count: number;
};
export type StagingUnmapped = {
  erp_id: string; part_type: string | null; components: string[];
};
export type StagingList = {
  from: string; to: string; window_hours: number;
  schedule_id: string | null; is_stale: boolean; note: string | null;
  /** BUY components whose BOM line has no consumed-at-step: the job needs them but
   *  nothing says at which bench, so they can't appear on any station's list. */
  unmapped: StagingUnmapped[];
  stations: StagingStation[];
};
export const stagingListOptions = (workCenterId?: string, hours = 8) =>
  queryOptions({
    queryKey: ["staging-list", workCenterId ?? null, hours],
    queryFn: () =>
      api.api_WorkCenters_staging_list_retrieve({
        queries: { ...(workCenterId ? { work_center: workCenterId } : {}), hours },
      }) as Promise<StagingList>,
  });

export function useStagingList(workCenterId?: string, hours = 8) {
  return useQuery(stagingListOptions(workCenterId, hours));
}

/** Mark a job's material staged at its bench (or take it back). */
export function useMarkStaged() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { work_order: string; step: string; staged: boolean; note?: string }) =>
      api.api_WorkCenters_mark_staged_create(v),
    onSuccess: () => qc.invalidateQueries(underRoot(ROOT.stagingList)),
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't update staging"),
  });
}

/** Record what was ACTUALLY pulled for one material on one job-operation.
 *
 *  Confirming sends the planned lots back; deviating sends what was really taken. Both
 *  are the same call — the difference is only which lots go in it. Recording either
 *  reserves the stock (so a second sheet can't promise the same units) and makes
 *  consumption draw those lots instead of re-deriving FEFO. */
export function useRecordPick() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: {
      work_order: string; step: string; material: string;
      /** Which subject `material` names. A Material and a PartTypes can hold the same
       *  uuid, so the id alone doesn't say which FK to write — the row echoes back the
       *  `kind` it came from rather than the server guessing. Omitted = MATERIAL. */
      kind?: "MATERIAL" | "PART_TYPE";
      qty: number; qty_required?: number;
      lots: { lot_id: string; lot_number?: string; qty: number }[];
    }) => api.api_WorkCenters_record_pick_create(v),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.stagingList));
      // Reserved stock changes what every other planning surface can promise.
      qc.invalidateQueries(underRoot(ROOT.planning));
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't record the pick"),
  });
}

/** "Why isn't this on the board?" — open work the active schedule doesn't cover, each
 *  row carrying the single most actionable reason and the fix for it. */
export type UnscheduledReason =
  | "on_hold" | "no_process" | "no_open_units" | "no_routing" | "no_timings"
  | "unstaffable" | "outside_horizon" | "material_gated" | "material_short"
  | "stale_schedule" | "not_solved";
export type UnscheduledRow = {
  work_order_id: string; erp_id: string; part_type: string | null;
  process: string | null; status: string; priority: number; quantity: number;
  due_date: string | null; expected_start: string | null;
  open_units: number; scheduled_units: number;
  reason: UnscheduledReason; reason_label: string; detail: string; fix: string;
};
export type UnscheduledDiagnosis = {
  schedule_id: string | null; solved_at: string | null; is_stale: boolean;
  horizon_start: string; horizon_end: string;
  open_work_orders: number; open_units: number; unscheduled_work_orders: number;
  counts: Record<string, number>;
  work_orders: UnscheduledRow[];
};
export const unscheduledOptions = (enabled = true) =>
  queryOptions({
    queryKey: ["schedule", "unscheduled"],
    enabled,
    // Re-derives the solver's inputs (routing, timings, training, material gates), so
    // it isn't free. The board carries a live count, hence always-on but long-lived.
    staleTime: 60_000,
    queryFn: () =>
      api.api_Schedules_unscheduled_retrieve() as Promise<UnscheduledDiagnosis>,
  });

export function useUnscheduled(enabled = true) {
  return useQuery(unscheduledOptions(enabled));
}

/** Per-WO material requirements — the "what this job needs" readout (picklist-lite):
 *  top-level BOM components × WO qty, bucketed by consumed-at-step, with a shortage flag. */
export type MaterialRequirementRow = {
  component: string; kind: string; source: string; quantity: number;
  unit_of_measure: string; consumed_at_step: string | null;
  on_hand: number; incoming: number;
  /** What the core bank could yield once torn down. NOT netted into `short_qty` —
   *  teardown has not happened, so it is a forecast beside facts. */
  recoverable?: number;
  short_qty: number; status: string; is_optional: boolean;
  lead_time_days: number | null; need_by: string | null; order_by: string | null;
};
export const workOrderMaterialRequirementsOptions = (id: string | null) =>
  queryOptions({
    queryKey: ["work-order", "material-requirements", id],
    queryFn: id
      ? async () =>
          ((await api.api_WorkOrders_material_requirements_retrieve({
            params: { id },
          })) as { rows?: MaterialRequirementRow[] }).rows ?? []
      : skipToken,
  });

export function useWorkOrderMaterialRequirements(id: string | null) {
  return useQuery(workOrderMaterialRequirementsOptions(id));
}

/** Make-up gap for a work order — good owed vs. still alive; `shortfall` is what a
 *  make-up would create. Refetched when the edit dialog opens. */
export const makeupStatusOptions = (id: string | null) =>
  queryOptions({
    queryKey: ["work-order", "makeup", id],
    queryFn: id
      ? () => api.api_WorkOrders_makeup_status_retrieve({ params: { id } })
      : skipToken,
  });

export function useMakeupStatus(id: string | null) {
  return useQuery(makeupStatusOptions(id));
}

/** Planner-confirmed make-up: spawn replacement parts to cover the shortfall. */
export function useCreateMakeup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_WorkOrders_create_makeup_create(undefined, { params: { id } }),
    onSuccess: (_data, id) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(makeupStatusOptions(id));
      toast.success("Make-up parts created");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't create make-up parts"),
  });
}

/** PATCH a work order's schedule-relevant attributes (priority / due / release). */
export function useUpdateWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_WorkOrders_partial_update(body, { params: { id } }),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success("Work order updated — re-solve to apply");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't update work order"),
  });
}

/** Set a WO's quantity (adds parts, or cancels unstarted parts). */
export function useSetWorkOrderQuantity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: number }) =>
      api.api_WorkOrders_set_quantity_create({ quantity }, { params: { id } }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      const msg = r?.added ? `Added ${r.added} part(s)` : r?.cancelled ? `Cancelled ${r.cancelled} unstarted part(s)` : "Quantity unchanged";
      toast.success(`${msg} — re-solve to apply`);
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't change quantity"),
  });
}

/** Put a work order on hold (drops it from the schedule until released). */
/* --- Release gate ---------------------------------------------------------
 * Only gates the solver when the tenant's release_mode is "manual"; under "auto"
 * these still work and record the stamp, they just don't filter anything. */

export type ReleaseCheck = { code: string; detail: string };
export type ReleaseReadiness = {
  work_order_id: string; erp_id: string; ok: boolean;
  blockers: ReleaseCheck[]; warnings: ReleaseCheck[];
};

/** Would this work order release clean? Fetched when the edit dialog opens. */
export const releaseReadinessOptions = (id: string | null) =>
  queryOptions({
    queryKey: ["work-order", "release-readiness", id],
    queryFn: id
      ? () =>
          api.api_WorkOrders_release_readiness_retrieve({
            params: { id },
          }) as Promise<ReleaseReadiness>
      : skipToken,
  });

export function useReleaseReadiness(id: string | null) {
  return useQuery(releaseReadinessOptions(id));
}

/** Authorize a work order for scheduling. A blocked order comes back 409 with its
 *  blockers — re-call with `override_reason` to release anyway (it's recorded). */
export function useReleaseForScheduling() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, override_reason }: { id: string; override_reason?: string }) =>
      api.api_WorkOrders_release_create(
        { override_reason: override_reason ?? "" },
        { params: { id } }
      ),
    onSuccess: (_d, v) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      // Releasing changes what the rough-cut layer shows — the order leaves the
      // release list and its load stops being provisional.
      qc.invalidateQueries(underRoot(ROOT.planning));
      toast.success(
        v.override_reason
          ? "Released with an override — re-solve to plan it"
          : "Released — re-solve to plan it"
      );
    },
    // 409 is the advisory gate, not a failure: the dialog shows the blockers and
    // offers the override, so don't shout an error toast over it.
    onError: (e: any) => {
      if (e?.response?.status !== 409) {
        toast.error(e?.response?.data?.detail ?? "Couldn't release the work order");
      }
    },
  });
}

/** The planner's "what can I pull in?" inbox — open work orders awaiting release,
 *  each with its readiness already evaluated. */
export type ReleaseQueueRow = {
  id: string; erp_id: string; part_type: string | null; process: string | null;
  status: string; priority: number; quantity: number; open_units: number;
  due_date: string | null; ready: boolean;
  blockers: ReleaseCheck[]; warnings: ReleaseCheck[];
};
export type ReleaseQueue = {
  release_mode: string; count: number; work_orders: ReleaseQueueRow[];
  recommendation?: ReleaseRecommendation;
};
export const releaseQueueOptions = (enabled = true) =>
  queryOptions({
    queryKey: ["work-order", "release-queue"],
    enabled,
    // Evaluates readiness AND the workload-control recommendation for the whole
    // queue, so it isn't free — the toolbar carries a live count, hence long-lived.
    // Both ride one payload: the dialog needs them together, they share reference
    // data, and the generated zodios client is at TypeScript's instantiation
    // ceiling (~1000 endpoints), so adding paths breaks type inference app-wide.
    staleTime: 60_000,
    queryFn: () =>
      api.api_WorkOrders_release_queue_retrieve() as Promise<ReleaseQueue>,
  });

export function useReleaseQueue(enabled = true) {
  return useQuery(releaseQueueOptions(enabled));
}

/** What workload control would release now, and why. Advisory — calling this
 *  releases nothing; it returns a recommended set plus the load arithmetic. */
export type ReleaseResource = {
  name: string; committed_hours: number; norm_hours: number;
  capacity_hours: number; utilization: number | null;
};
export type ReleaseRecDecision = {
  work_order_id: string; erp_id: string; release: boolean; reason: string;
  blocking_resource: string | null; hours: Record<string, number>;
};
export type ReleaseRecommendation = {
  policy: string; policy_label: string; norm_pct: number; window_days: number;
  resources: ReleaseResource[]; decisions: ReleaseRecDecision[];
  released_count: number; held_count: number;
};
/* Delivered on the release-queue payload, not its own endpoint — the dialog always
 * needs both together, and the generated zodios client is at TypeScript's type
 * instantiation ceiling (see the note in useReleaseQueue). */

/** Release many at once. Per-order outcome — the response reports which went and
 *  which were refused, so a partial batch is a normal result, not an error. */
export function useBulkRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, override_reason }: { ids: string[]; override_reason?: string }) =>
      api.api_WorkOrders_bulk_release_create(
        { ids, override_reason: override_reason ?? "" }
      ) as Promise<{ released: number; blocked: number; results: any[] }>,
    onSuccess: (d) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      if (d.blocked > 0) {
        toast.warning(
          `Released ${d.released} — ${d.blocked} need a reason before they can go.`
        );
      } else {
        toast.success(`Released ${d.released} — re-solve to plan them`);
      }
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't release the work orders"),
  });
}

/** Withdraw authorization — the solver stops planning it under manual mode. */
export function useUnreleaseForScheduling() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_WorkOrders_unrelease_create(undefined, { params: { id } }),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success("Release withdrawn — re-solve to drop it");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't withdraw the release"),
  });
}

export function useHoldWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.api_WorkOrders_place_on_hold_create({ reason }, { params: { id } }),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success("Work order held — re-solve to drop it");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't hold work order"),
  });
}

/** Release a work order's hold (returns it to the schedule). */
export function useReleaseWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_WorkOrders_clear_hold_create(undefined, { params: { id } }),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success("Hold cleared — re-solve to reschedule");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't release hold"),
  });
}

/** Cancel a work order (drops it from scheduling). Refused if parts have shipped. */
export function useCancelWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_WorkOrders_cancel_create(undefined, { params: { id } }),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success("Work order cancelled");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't cancel work order"),
  });
}

/** Eligible machines + qualified operators for a task's step (reassign dropdowns). */
export const reassignOptionsOptions = (taskId: string | null) =>
  queryOptions({
    queryKey: ["reassign-options", taskId],
    queryFn: taskId
      ? () => api.api_ScheduledTasks_reassign_options_retrieve({ params: { id: taskId } })
      : skipToken,
  });

export function useReassignOptions(taskId: string | null) {
  return useQuery(reassignOptionsOptions(taskId));
}

/** Move a task onto a specific machine (+ pin). Warns if the machine isn't eligible. */
export function useReassignMachine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, machine_id }: { id: string; machine_id: string }) =>
      api.api_ScheduledTasks_reassign_machine_create(
        { machine_id }, { params: { id } }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      if (r?.warning) toast.warning(r.warning);
      else toast.success("Machine reassigned");
    },
    onError: () => toast.error("Couldn't reassign machine"),
    // Own message is specific; the global handler would add a vaguer duplicate.
    meta: { suppressGlobalError: true },
  });
}

/** Assign / clear the operator on a task. Warns if the operator isn't qualified. */
export function useReassignOperator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, operator_id }: { id: string; operator_id: number | null }) =>
      api.api_ScheduledTasks_reassign_operator_create(
        { operator_id }, { params: { id } }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      if (r?.warning) toast.warning(r.warning);
      else toast.success("Operator updated");
    },
    onError: () => toast.error("Couldn't update operator"),
    // Own message is specific; the global handler would add a vaguer duplicate.
    meta: { suppressGlobalError: true },
  });
}

/** Move several selected tasks onto one machine (+ pin). Warns per ineligible step. */
export function useBulkReassignMachine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, machine_id }: { task_ids: string[]; machine_id: string }) =>
      api.api_ScheduledTasks_bulk_reassign_machine_create({ task_ids, machine_id }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      const warnings: string[] = r?.warnings ?? [];
      if (warnings.length) warnings.forEach((w) => toast.warning(w));
      else toast.success(`Reassigned ${r?.changed ?? 0} tasks`);
    },
    onError: () => toast.error("Couldn't reassign the selection"),
    // Own message is specific; the global handler would add a vaguer duplicate.
    meta: { suppressGlobalError: true },
  });
}

/** Assign / clear one operator across several selected tasks. Warns per ineligible step. */
export function useBulkReassignOperator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, operator_id }: { task_ids: string[]; operator_id: number | null }) =>
      api.api_ScheduledTasks_bulk_reassign_operator_create({ task_ids, operator_id }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      const warnings: string[] = r?.warnings ?? [];
      if (warnings.length) warnings.forEach((w) => toast.warning(w));
      else toast.success(`Updated ${r?.changed ?? 0} tasks`);
    },
    onError: () => toast.error("Couldn't update the selection"),
  });
}

/** Processes available to plan a new work order against.
 *
 *  APPROVED only. An unapproved routing is a draft someone is still editing — releasing
 *  real production against it means building to an uncontrolled process, and the steps
 *  can change underneath the running job. The server enforces this too; filtering here
 *  keeps the choice out of the picker rather than failing after the planner picks it.
 */
export const processesForPlanningOptions = () =>
  queryOptions({
    queryKey: ["processes", "for-planning"],
    queryFn: () =>
      api.api_Processes_list({ queries: { limit: 500, status: "APPROVED" } }),
  });

export function useProcesses() {
  return useQuery(processesForPlanningOptions());
}

/** Create a new work order + its parts (the Gantt 'add work' action). */
export function usePlanWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.api_Schedules_plan_work_order_create>[0]) =>
      api.api_Schedules_plan_work_order_create(body),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      toast.success(`Work order ${r?.ERP_id ?? ""} created — re-solve to schedule it`);
      // Yield gross-up: started more than requested to still finish the good count.
      if (r?.yield?.started && r?.yield?.target_good) {
        toast.info(
          `Started ${r.yield.started} to yield ${r.yield.target_good} good (expected scrap)`
        );
      }
      // BOM auto-explosion ran server-side: report component WOs made / netted / short.
      const ex = r?.explosion;
      if (ex?.created_count) {
        toast.success(`Generated ${ex.created_count} in-house component work order(s) from the BOM`);
      }
      if (ex?.short?.length) {
        toast.warning(
          `${ex.short.length} MAKE component(s) couldn't be built automatically: ` +
            ex.short.map((s: any) => `${s.component} (${s.reason})`).join("; ")
        );
      }
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't create the work order"),
  });
}

/** (Re)explode an existing work order's BOM into pegged component WOs. */
export function useExplodeWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ work_order_id, create = true }: { work_order_id: string; create?: boolean }) =>
      api.api_Schedules_explode_work_order_create({ work_order_id, create }),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries(underRoot(ROOT.workOrder));
      const made = r?.created_count ?? 0;
      if (made) toast.success(`Generated ${made} component work order(s)`);
      else toast.success("BOM exploded — nothing new needed");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't explode the BOM"),
  });
}

/** Work-hours shift calendar (the solver's working windows come from these). */
export const shiftsOptions = () =>
  queryOptions({
    queryKey: ["shifts"],
    queryFn: () =>
      api.api_Shifts_list({ queries: { ordering: "start_time", limit: 200 } }),
  });

export function useShifts() {
  return useQuery(shiftsOptions());
}

/** Create (no id) or update (with id) a shift. */
export function useSaveShift() {
  const qc = useQueryClient();
  return useMutation({
    // Typed from the create request: the settings form always sends name /
    // code / start_time / end_time, and the update path takes a subset.
    mutationFn: ({ id, ...body }: { id?: string } & Parameters<typeof api.api_Shifts_create>[0]) =>
      id
        ? api.api_Shifts_partial_update(body, { params: { id } })
        : api.api_Shifts_create(body),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.shifts));
      // A content edit forks the shift to a NEW id and repoints every
      // User.default_shift server-side — cached user/auth payloads still
      // hold the old id, which zeroes the calendar's headcount badges and
      // breaks the "My crew" preset until their 5-min staleTime expires.
      qc.invalidateQueries(underRoot("user"));
      qc.invalidateQueries(underRoot("authUser"));
      toast.success("Shift saved");
    },
    onError: () => toast.error("Couldn't save shift — is the code unique?"),
  });
}

/** Remove a shift. */
export function useDeleteShift() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_Shifts_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.shifts));
      toast.success("Shift removed");
    },
    onError: () => toast.error("Couldn't remove shift"),
  });
}

// --- Tooling / shared resources (fixtures, cutting tools, dies, NC programs) ---

/** Paginated list for the tooling editor table (ModelEditorPage shape). */
export const fixturesListOptions = (params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) => {
  const { offset, limit, ordering, search, filters } = params;
  return queryOptions({
    queryKey: ["fixtures", { offset, limit, ordering, search, filters }],
    queryFn: () =>
      api.api_Fixtures_list({
        queries: { offset, limit, ordering, search, ...(filters ?? {}) },
      }),
  });
};

export function useFixturesList(params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) {
  return useQuery(fixturesListOptions(params));
}

/** One tooling resource (for the edit form). */
export const retrieveFixtureOptions = (id?: string) =>
  queryOptions({
    queryKey: ["fixture", id],
    queryFn: id ? () => api.api_Fixtures_retrieve({ params: { id } }) : skipToken,
  });

export function useRetrieveFixture(id?: string) {
  return useQuery(retrieveFixtureOptions(id));
}

/** Create a tooling resource. */
export function useCreateFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.api_Fixtures_create>[0]) =>
      api.api_Fixtures_create(body),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.fixtures));
      invalidateSchedule(qc);
    },
  });
}

/** Update a tooling resource. */
export function useUpdateFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_Fixtures_partial_update(body, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.fixtures));
      invalidateSchedule(qc);
    },
  });
}

/** Remove a tooling resource. */
export function useDeleteFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_Fixtures_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(underRoot(ROOT.fixtures));
      invalidateSchedule(qc);
      toast.success("Resource removed");
    },
    onError: () => toast.error("Couldn't remove resource"),
  });
}

/** A process's detail, including its ordered `process_steps` — powers the tooling form's
 *  cascading Process → Step picker. */
export const processDetailOptions = (id?: string) =>
  queryOptions({
    queryKey: ["process-detail", id],
    queryFn: id ? () => api.api_Processes_retrieve({ params: { id } }) : skipToken,
  });

export function useProcessDetail(id?: string) {
  return useQuery(processDetailOptions(id));
}

/** Pin / unpin a task (planner lock). */
export function usePinTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_pinned }: { id: string; is_pinned: boolean }) =>
      api.api_ScheduledTasks_pin_create({ is_pinned }, {
        params: { id },
      }),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Drag-to-reschedule: pin a task at a new start (server keeps its duration).
 * The server 422s with a `detail` reason if the drop breaks a local constraint. */
/** Undo the most recent manual edit to the active schedule.
 *
 *  A drag now ripples: one move can shift a dozen downstream operations, and nobody
 *  restores twelve bar positions by hand. Undo is what makes a cascade safe to try. */
export function useUndoScheduleEdit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_undo_create(undefined as never) as Promise<{
      kind: string; task_count: number;
    }>,
    onSuccess: (r) => {
      invalidateSchedule(qc);
      toast.success(`Undid ${r.kind} — ${r.task_count} task${r.task_count === 1 ? "" : "s"} restored`);
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(detail ?? "Nothing to undo");
    },
    meta: { suppressGlobalError: true },
  });
}

export type ScheduleOverlap = {
  machine: string; machine_name: string;
  tasks: [string, string]; step_names: [string, string];
  overlap_start: string; overlap_end: string;
  pinned: [boolean, boolean];
};

/** Machine double-bookings in the active schedule.
 *
 *  A ripple follows the ROUTE and leaves resource contention to CP-SAT, which is the
 *  right division but means a manual move can silently double-book a machine. This is
 *  how that becomes visible before the next solve quietly undoes a decision. */
export function useScheduleViolations() {
  return useQuery({
    queryKey: ["planning", "schedule-violations"] as const,
    queryFn: () => api.api_Schedules_violations_retrieve() as Promise<{
      overlaps: ScheduleOverlap[]; task_ids: string[];
    }>,
  });
}

export function useMoveTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, start_time }: { id: string; start_time: string }) =>
      api.api_ScheduledTasks_move_create({ start_time }, {
        params: { id },
      }) as Promise<{ id: string; rippled_count: number; rippled_task_ids: string[] }>,
    // Refetch on both outcomes so a SUCCESSFUL move settles to the server's truth.
    // A rejected one is not undone here: the refetched data is deeply equal, and
    // React Query's structural sharing then returns the same object reference, so
    // nothing downstream re-renders. The bar's own rollback handles that case.
    onSettled: () => invalidateSchedule(qc),
    // The drag handler toasts the reason and rolls the bar back.
    meta: { suppressGlobalError: true },
  });
}
