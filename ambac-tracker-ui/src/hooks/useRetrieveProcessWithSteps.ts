import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type ProcessWithSteps = Schema<"Processes">;

export const retrieveProcessWithStepsOptions = (queries: Parameters<typeof api.api_Processes_with_steps_retrieve>[0]) => queryOptions({
    queryKey: ["process-with-steps", queries] as const,
    queryFn: () => api.api_Processes_with_steps_retrieve(queries) as unknown as Promise<ProcessWithSteps>,
});

export function useRetrieveProcessWithSteps(queries: Parameters<typeof api.api_Processes_with_steps_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveProcessWithStepsOptions(queries), enabled: options?.enabled ?? true });
}