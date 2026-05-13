import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type ProcessesResponse = Schema<"Processes">;

export const retrieveProcessOptions = (queries: Parameters<typeof api.api_Processes_retrieve>[0]) => queryOptions({
    queryKey: ["process", queries] as const,
    queryFn: () => api.api_Processes_retrieve(queries) as Promise<ProcessesResponse>,
});

export function useRetrieveProcess(queries: Parameters<typeof api.api_Processes_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveProcessOptions(queries), enabled: options?.enabled ?? true });
}