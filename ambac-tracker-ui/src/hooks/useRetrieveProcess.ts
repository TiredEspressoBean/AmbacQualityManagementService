import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type ProcessesResponse = Schema<"Processes">;

export function useRetrieveProcess(
    queries: Parameters<typeof api.api_Processes_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<ProcessesResponse>({
        queryKey: ["process", queries],
        queryFn: () => api.api_Processes_retrieve(queries) as Promise<ProcessesResponse>,
        enabled: options?.enabled ?? true,
    });
}