/** Labor & plant calendar CRUD — backs the scheduling calendar page.
 *
 *  Two backing resources, shown on one calendar:
 *  - PlantCalendarException: dated, plant-wide closures (blocks machines + operators).
 *  - LaborCalendarBlock: operator non-working time (PTO / sick / meeting / break),
 *    one-off or weekly, company-wide or per person (operators only).
 */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type PlantClosure = components["schemas"]["PlantCalendarException"];
export type LaborBlock = components["schemas"]["LaborCalendarBlock"];
export type Overtime = components["schemas"]["OvertimeWindow"];

const CLOSURE_KEY = ["plant-closures"] as const;
const BLOCK_KEY = ["labor-blocks"] as const;
const OVERTIME_KEY = ["overtime-windows"] as const;

export const plantClosuresOptions = () =>
  queryOptions({
    queryKey: CLOSURE_KEY,
    queryFn: async () =>
      ((await api.api_PlantCalendarExceptions_list({
        queries: { limit: 500, ordering: "start_time" },
      })) as { results?: PlantClosure[] }).results ?? [],
    staleTime: 30_000,
  });

export const laborBlocksOptions = () =>
  queryOptions({
    queryKey: BLOCK_KEY,
    queryFn: async () =>
      ((await api.api_LaborCalendarBlocks_list({
        queries: { limit: 500, ordering: "start_time" },
      })) as { results?: LaborBlock[] }).results ?? [],
    staleTime: 30_000,
  });

export const overtimeWindowsOptions = () =>
  queryOptions({
    queryKey: OVERTIME_KEY,
    queryFn: async () =>
      ((await api.api_OvertimeWindows_list({
        queries: { limit: 500, ordering: "start_date" },
      })) as { results?: Overtime[] }).results ?? [],
    staleTime: 30_000,
  });

export function usePlantClosures() {
  return useQuery(plantClosuresOptions());
}

export function useLaborBlocks() {
  return useQuery(laborBlocksOptions());
}

export function useOvertimeWindows() {
  return useQuery(overtimeWindowsOptions());
}

export function useCreatePlantClosure() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.api_PlantCalendarExceptions_create>[0]) =>
      api.api_PlantCalendarExceptions_create(body),
    onSuccess: () => {
      qc.invalidateQueries(plantClosuresOptions());
      toast.success("Closure added");
    },
    onError: () => toast.error("Couldn't add closure"),
  });
}

export function useDeletePlantClosure() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_PlantCalendarExceptions_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(plantClosuresOptions());
      toast.success("Closure removed");
    },
    onError: () => toast.error("Couldn't remove closure"),
  });
}

export function useCreateLaborBlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.api_LaborCalendarBlocks_create(body),
    onSuccess: () => {
      qc.invalidateQueries(laborBlocksOptions());
      toast.success("Added to the calendar");
    },
    onError: () => toast.error("Couldn't save — check the required fields"),
  });
}

export function useDeleteLaborBlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_LaborCalendarBlocks_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(laborBlocksOptions());
      toast.success("Removed");
    },
    onError: () => toast.error("Couldn't remove"),
  });
}

export function useCreateOvertime() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.api_OvertimeWindows_create>[0]) =>
      api.api_OvertimeWindows_create(body),
    onSuccess: () => {
      qc.invalidateQueries(overtimeWindowsOptions());
      toast.success("Overtime added");
    },
    onError: () => toast.error("Couldn't save — check the required fields"),
  });
}

export function useDeleteOvertime() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_OvertimeWindows_destroy(undefined, { params: { id } }),
    onSuccess: () => {
      qc.invalidateQueries(overtimeWindowsOptions());
      toast.success("Removed");
    },
    onError: () => toast.error("Couldn't remove"),
  });
}
