import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveProcessWithSteps(
    queries: Parameters<typeof api.api_Processes_with_steps_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["process-with-steps", queries],
        queryFn: () => api.api_Processes_with_steps_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}