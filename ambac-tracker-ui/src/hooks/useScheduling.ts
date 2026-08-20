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
  labels: { done: (result: any) => string; verb: string }
) {
  const qc = useQueryClient();
  const [taskId, setTaskId] = useState<string | null>(null);
  const labelsRef = useRef(labels);
  labelsRef.current = labels;

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
