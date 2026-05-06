import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type ProcessWithSteps = Schema<"Processes">;

export function useRetrieveProcessWithSteps(
    queries: Parameters<typeof api.api_Processes_with_steps_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<ProcessWithSteps>({
        queryKey: ["process-with-steps", queries],
        queryFn: () => api.api_Processes_with_steps_retrieve(queries) as Promise<ProcessWithSteps>,
        enabled: options?.enabled ?? true,
    });
}