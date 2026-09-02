// Hooks for the CP-SAT scheduling API (solve / dispatch / read / pin).
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";

/** The active schedule's run metadata (null when none has been solved yet). */
export function useCurrentSchedule() {
  return useQuery({
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
}

/** Scheduled tasks (Gantt rows) for a schedule. */
export function useScheduledTasks(scheduleId?: string) {
  return useQuery({
    queryKey: ["scheduled-tasks", scheduleId],
    enabled: !!scheduleId,
    queryFn: () =>
      // Fetch the whole schedule (default page size is 25) so every machine/operator
      // lane is populated, not just the earliest 25 tasks.
      api.api_ScheduledTasks_list({
        queries: { schedule: scheduleId, ordering: "start_time", limit: 2000 },
      } as never),
  });
}

/** Re-anchor a work-order batch (many parts at one op) to a new start. 422s with a
 * `detail` reason if any part breaks a local constraint. */
export function useMoveBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, start_time }: { task_ids: string[]; start_time: string }) =>
      api.api_ScheduledTasks_move_batch_create({ task_ids, start_time } as never),
    onSettled: () => invalidateSchedule(qc),
  });
}

/** Pin / unpin every part of a work-order batch. */
export function usePinBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, is_pinned }: { task_ids: string[]; is_pinned: boolean }) =>
      api.api_ScheduledTasks_pin_batch_create({ task_ids, is_pinned } as never),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Tenant working windows over the active schedule's horizon (for shift shading). */
export function useWorkingWindows(scheduleId?: string) {
  return useQuery({
    queryKey: ["schedule", "working-windows", scheduleId],
    enabled: !!scheduleId,
    queryFn: () => api.api_Schedules_working_windows_retrieve(),
  });
}

function invalidateSchedule(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["schedule"] });
  qc.invalidateQueries({ queryKey: ["scheduled-tasks"] });
}

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
  });

  const status = useQuery({
    queryKey: ["solve-status", taskId],
    enabled: !!taskId,
    queryFn: () =>
      api.api_Schedules_solve_status_retrieve({ queries: { task_id: taskId } } as never),
    // Poll while the task is queued/running; stop once it's terminal.
    refetchInterval: (q) => {
      const s = (q.state.data as any)?.state;
      return s === "SUCCESS" || s === "FAILURE" ? false : 1500;
    },
  });

  useEffect(() => {
    const d = status.data as any;
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
    () => api.api_Schedules_solve_create(undefined as never) as Promise<{ task_id: string }>,
    { verb: "the solve", done: (r) => `Schedule solved (${r?.solver_status ?? "done"})` }
  );
}

/** Run a what-if solve in the background — produces a draft, live untouched.
 * `onReady` fires when the draft is solved (used to auto-switch the board to the
 * draft view, so the what-if shows itself instead of hiding behind a toggle). */
export function useSolveDraft(onReady?: () => void) {
  return useAsyncScheduleTask(
    () => api.api_Schedules_solve_draft_create(undefined as never) as Promise<{ task_id: string }>,
    { verb: "the what-if", done: () => "What-if draft ready — showing it now" },
    onReady
  );
}

/** The pending what-if draft (null when none). */
export function useDraftSchedule() {
  return useQuery({
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
}

/** Live-vs-draft comparison (summaries + moved-task count); only when a draft exists. */
export function useCompareDraft(enabled: boolean) {
  return useQuery({
    queryKey: ["schedule", "compare"],
    enabled,
    queryFn: () => api.api_Schedules_compare_retrieve(),
  });
}

/** Promote the draft to the live schedule. */
export function useCommitDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_commit_create(undefined as never),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Throw the draft away, leaving live untouched. */
export function useDiscardDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_discard_create(undefined as never),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Assign operators to the active schedule (Layer 2) in the background. */
export function useDispatchSchedule() {
  return useAsyncScheduleTask(
    () => api.api_Schedules_dispatch_create(undefined as never) as Promise<{ task_id: string }>,
    {
      verb: "dispatch",
      done: (r) =>
        r?.covered != null
          ? `Dispatched: ${r.covered}/${r.attended} attended tasks covered`
          : "Dispatch complete",
    }
  );
}

/** The tenant's solver knobs (time limit, fences, penalties, labor model). */
export function useOptimizationConfig() {
  return useQuery({
    queryKey: ["schedule", "config"],
    queryFn: () => api.api_Schedules_config_retrieve(),
  });
}

/** Update the tenant's solver knobs (partial). */
export function useUpdateOptimizationConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Record<string, unknown>) =>
      api.api_Schedules_config_partial_update(patch as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedule", "config"] });
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
      api.api_ScheduledTasks_batch_membership_create({ task_ids, merge } as never),
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
export function useWorkOrder(id: string | null) {
  return useQuery({
    queryKey: ["work-order", id],
    enabled: !!id,
    queryFn: () => api.api_WorkOrders_retrieve({ params: { id } } as never),
  });
}

/** Operator shop-hours over a date range — on-shift (attendance) + direct (job) hours,
 *  from TimeEntry, scoped to shop-floor operators. */
export type OperatorHoursRow = {
  user_id: number; name: string; on_shift_hours: number; direct_hours: number;
};
export function useOperatorHours(start: string, end: string) {
  return useQuery({
    queryKey: ["operator-hours", start, end],
    queryFn: async () =>
      ((await api.api_Schedules_operator_hours_retrieve({
        queries: { start, end },
      } as never)) as { rows?: OperatorHoursRow[] }).rows ?? [],
  });
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
export function useRequirements() {
  return useQuery({
    queryKey: ["schedule", "requirements"],
    queryFn: () =>
      api.api_Schedules_requirements_retrieve() as Promise<{
        source: SourceRow[]; produce: ProduceRow[]; tooling: ToolingRow[];
      }>,
  });
}

/* --- Rough-cut capacity planning ------------------------------------------
 * The coarse layer above CP-SAT: monthly capacity-vs-load arithmetic over a horizon
 * far past what the solver plans in detail, and the "could we take this order?" quote
 * built on it. */

export type CapacityBucket = {
  bucket: string; capacity_hours: number; load_hours: number;
  utilization: number | null;
};
export type CapacityLoad = {
  buckets: string[];
  labor: { name: string; crew_size: number; series: CapacityBucket[] };
  work_centers: { id: string; name: string; series: CapacityBucket[] }[];
};
export function useCapacityLoad(months = 12) {
  return useQuery({
    queryKey: ["planning", "capacity-load", months],
    queryFn: () =>
      api.api_Schedules_capacity_load_retrieve({
        queries: { months },
      } as never) as Promise<CapacityLoad>,
  });
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
export function useCapableToPromise(
  args: { part_type: string; quantity: number; target_date: string; months?: number } | null
) {
  return useQuery({
    queryKey: ["planning", "ctp", args],
    enabled: !!args && !!args.part_type && args.quantity > 0 && !!args.target_date,
    queryFn: () =>
      api.api_Schedules_capable_to_promise_retrieve({
        queries: args,
      } as never) as Promise<CtpQuote>,
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
export function useUnscheduled(enabled = true) {
  return useQuery({
    queryKey: ["schedule", "unscheduled"],
    enabled,
    // Re-derives the solver's inputs (routing, timings, training, material gates), so
    // it isn't free. The board carries a live count, hence always-on but long-lived.
    staleTime: 60_000,
    queryFn: () =>
      api.api_Schedules_unscheduled_retrieve() as Promise<UnscheduledDiagnosis>,
  });
}

/** Per-WO material requirements — the "what this job needs" readout (picklist-lite):
 *  top-level BOM components × WO qty, bucketed by consumed-at-step, with a shortage flag. */
export type MaterialRequirementRow = {
  component: string; kind: string; source: string; quantity: number;
  unit_of_measure: string; consumed_at_step: string | null;
  on_hand: number; incoming: number; short_qty: number; status: string; is_optional: boolean;
  lead_time_days: number | null; need_by: string | null; order_by: string | null;
};
export function useWorkOrderMaterialRequirements(id: string | null) {
  return useQuery({
    queryKey: ["work-order", "material-requirements", id],
    enabled: !!id,
    queryFn: async () =>
      ((await api.api_WorkOrders_material_requirements_retrieve({
        params: { id },
      } as never)) as { rows?: MaterialRequirementRow[] }).rows ?? [],
  });
}

/** Make-up gap for a work order — good owed vs. still alive; `shortfall` is what a
 *  make-up would create. Refetched when the edit dialog opens. */
export function useMakeupStatus(id: string | null) {
  return useQuery({
    queryKey: ["work-order", "makeup", id],
    enabled: !!id,
    queryFn: () => api.api_WorkOrders_makeup_status_retrieve({ params: { id } } as never),
  });
}

/** Planner-confirmed make-up: spawn replacement parts to cover the shortfall. */
export function useCreateMakeup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_WorkOrders_create_makeup_create(undefined as never, { params: { id } } as never),
    onSuccess: (_data, id) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order", "makeup", id] });
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
      api.api_WorkOrders_partial_update(body as never, { params: { id } } as never),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_WorkOrders_set_quantity_create({ quantity } as never, { params: { id } } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
export function useReleaseReadiness(id: string | null) {
  return useQuery({
    queryKey: ["work-order", "release-readiness", id],
    enabled: !!id,
    queryFn: () =>
      api.api_WorkOrders_release_readiness_retrieve({
        params: { id },
      } as never) as Promise<ReleaseReadiness>,
  });
}

/** Authorize a work order for scheduling. A blocked order comes back 409 with its
 *  blockers — re-call with `override_reason` to release anyway (it's recorded). */
export function useReleaseForScheduling() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, override_reason }: { id: string; override_reason?: string }) =>
      api.api_WorkOrders_release_create(
        { override_reason: override_reason ?? "" } as never,
        { params: { id } } as never
      ),
    onSuccess: (_d, v) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
};
export function useReleaseQueue(enabled = true) {
  return useQuery({
    queryKey: ["work-order", "release-queue"],
    enabled,
    // Evaluates readiness for the whole queue (routing, timings, training, material),
    // so it isn't free — the toolbar carries a live count, hence long-lived.
    staleTime: 60_000,
    queryFn: () =>
      api.api_WorkOrders_release_queue_retrieve() as Promise<ReleaseQueue>,
  });
}

/** Release many at once. Per-order outcome — the response reports which went and
 *  which were refused, so a partial batch is a normal result, not an error. */
export function useBulkRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ids, override_reason }: { ids: string[]; override_reason?: string }) =>
      api.api_WorkOrders_bulk_release_create(
        { ids, override_reason: override_reason ?? "" } as never
      ) as Promise<{ released: number; blocked: number; results: any[] }>,
    onSuccess: (d) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_WorkOrders_unrelease_create(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_WorkOrders_place_on_hold_create({ reason } as never, { params: { id } } as never),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_WorkOrders_clear_hold_create(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_WorkOrders_cancel_create(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
      toast.success("Work order cancelled");
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? "Couldn't cancel work order"),
  });
}

/** Eligible machines + qualified operators for a task's step (reassign dropdowns). */
export function useReassignOptions(taskId: string | null) {
  return useQuery({
    queryKey: ["reassign-options", taskId],
    enabled: !!taskId,
    queryFn: () =>
      api.api_ScheduledTasks_reassign_options_retrieve({ params: { id: taskId } } as never),
  });
}

/** Move a task onto a specific machine (+ pin). Warns if the machine isn't eligible. */
export function useReassignMachine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, machine_id }: { id: string; machine_id: string }) =>
      api.api_ScheduledTasks_reassign_machine_create(
        { machine_id } as never, { params: { id } } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      if (r?.warning) toast.warning(r.warning);
      else toast.success("Machine reassigned");
    },
    onError: () => toast.error("Couldn't reassign machine"),
  });
}

/** Assign / clear the operator on a task. Warns if the operator isn't qualified. */
export function useReassignOperator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, operator_id }: { id: string; operator_id: string | null }) =>
      api.api_ScheduledTasks_reassign_operator_create(
        { operator_id } as never, { params: { id } } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      if (r?.warning) toast.warning(r.warning);
      else toast.success("Operator updated");
    },
    onError: () => toast.error("Couldn't update operator"),
  });
}

/** Move several selected tasks onto one machine (+ pin). Warns per ineligible step. */
export function useBulkReassignMachine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, machine_id }: { task_ids: string[]; machine_id: string }) =>
      api.api_ScheduledTasks_bulk_reassign_machine_create({ task_ids, machine_id } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      const warnings: string[] = r?.warnings ?? [];
      if (warnings.length) warnings.forEach((w) => toast.warning(w));
      else toast.success(`Reassigned ${r?.changed ?? 0} tasks`);
    },
    onError: () => toast.error("Couldn't reassign the selection"),
  });
}

/** Assign / clear one operator across several selected tasks. Warns per ineligible step. */
export function useBulkReassignOperator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ task_ids, operator_id }: { task_ids: string[]; operator_id: string | null }) =>
      api.api_ScheduledTasks_bulk_reassign_operator_create({ task_ids, operator_id } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      const warnings: string[] = r?.warnings ?? [];
      if (warnings.length) warnings.forEach((w) => toast.warning(w));
      else toast.success(`Updated ${r?.changed ?? 0} tasks`);
    },
    onError: () => toast.error("Couldn't update the selection"),
  });
}

/** Processes available to plan a new work order against. */
export function useProcesses() {
  return useQuery({
    queryKey: ["processes", "for-planning"],
    queryFn: () => api.api_Processes_list({ queries: { limit: 500 } } as never),
  });
}

/** Create a new work order + its parts (the Gantt 'add work' action). */
export function usePlanWorkOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.api_Schedules_plan_work_order_create(body as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
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
      api.api_Schedules_explode_work_order_create({ work_order_id, create } as never),
    onSuccess: (r: any) => {
      invalidateSchedule(qc);
      qc.invalidateQueries({ queryKey: ["work-order"] });
      const made = r?.created_count ?? 0;
      if (made) toast.success(`Generated ${made} component work order(s)`);
      else toast.success("BOM exploded — nothing new needed");
    },
    onError: (e: any) =>
      toast.error(e?.response?.data?.detail ?? "Couldn't explode the BOM"),
  });
}

/** Work-hours shift calendar (the solver's working windows come from these). */
export function useShifts() {
  return useQuery({
    queryKey: ["shifts"],
    queryFn: () =>
      api.api_Shifts_list({ queries: { ordering: "start_time", limit: 200 } } as never),
  });
}

/** Create (no id) or update (with id) a shift. */
export function useSaveShift() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id?: string } & Record<string, unknown>) =>
      id
        ? api.api_Shifts_partial_update(body as never, { params: { id } } as never)
        : api.api_Shifts_create(body as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shifts"] });
      // A content edit forks the shift to a NEW id and repoints every
      // User.default_shift server-side — cached user/auth payloads still
      // hold the old id, which zeroes the calendar's headcount badges and
      // breaks the "My crew" preset until their 5-min staleTime expires.
      qc.invalidateQueries({ queryKey: ["user"] });
      qc.invalidateQueries({ queryKey: ["authUser"] });
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
      api.api_Shifts_destroy(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shifts"] });
      toast.success("Shift removed");
    },
    onError: () => toast.error("Couldn't remove shift"),
  });
}

// --- Tooling / shared resources (fixtures, cutting tools, dies, NC programs) ---

/** Paginated list for the tooling editor table (ModelEditorPage shape). */
export function useFixturesList(params: {
  offset: number;
  limit: number;
  ordering?: string;
  search?: string;
  filters?: Record<string, string>;
}) {
  const { offset, limit, ordering, search, filters } = params;
  return useQuery({
    queryKey: ["fixtures", { offset, limit, ordering, search, filters }],
    queryFn: () =>
      api.api_Fixtures_list({
        queries: { offset, limit, ordering, search, ...(filters ?? {}) },
      } as never),
  });
}

/** One tooling resource (for the edit form). */
export function useRetrieveFixture(id?: string) {
  return useQuery({
    queryKey: ["fixture", id],
    enabled: !!id,
    queryFn: () => api.api_Fixtures_retrieve({ params: { id } } as never),
  });
}

/** Create a tooling resource. */
export function useCreateFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.api_Fixtures_create(body as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fixtures"] });
      invalidateSchedule(qc);
    },
  });
}

/** Update a tooling resource. */
export function useUpdateFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api.api_Fixtures_partial_update(body as never, { params: { id } } as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fixtures"] });
      invalidateSchedule(qc);
    },
  });
}

/** Remove a tooling resource. */
export function useDeleteFixture() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_Fixtures_destroy(undefined as never, { params: { id } } as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fixtures"] });
      invalidateSchedule(qc);
      toast.success("Resource removed");
    },
    onError: () => toast.error("Couldn't remove resource"),
  });
}

/** A process's detail, including its ordered `process_steps` — powers the tooling form's
 *  cascading Process → Step picker. */
export function useProcessDetail(id?: string) {
  return useQuery({
    queryKey: ["process-detail", id],
    enabled: !!id,
    queryFn: () => api.api_Processes_retrieve({ params: { id } } as never),
  });
}

/** Pin / unpin a task (planner lock). */
export function usePinTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_pinned }: { id: string; is_pinned: boolean }) =>
      api.api_ScheduledTasks_pin_create({ is_pinned } as never, {
        params: { id },
      } as never),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Drag-to-reschedule: pin a task at a new start (server keeps its duration).
 * The server 422s with a `detail` reason if the drop breaks a local constraint. */
export function useMoveTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, start_time }: { id: string; start_time: string }) =>
      api.api_ScheduledTasks_move_create({ start_time } as never, {
        params: { id },
      } as never),
    // Refetch on both success and failure so bars settle to the server's truth
    // (a rejected move leaves data unchanged → the bar snaps back).
    onSettled: () => invalidateSchedule(qc),
  });
}
