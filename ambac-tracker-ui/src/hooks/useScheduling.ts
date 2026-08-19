// Hooks for the CP-SAT scheduling API (solve / dispatch / read / pin).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

function invalidateSchedule(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["schedule"] });
  qc.invalidateQueries({ queryKey: ["scheduled-tasks"] });
}

/** Run the Layer-1 solver (supersedes the active schedule). */
export function useSolveSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_solve_create(undefined as never),
    onSuccess: () => invalidateSchedule(qc),
  });
}

/** Assign operators to the active schedule (Layer 2). */
export function useDispatchSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.api_Schedules_dispatch_create(undefined as never),
    onSuccess: () => invalidateSchedule(qc),
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
