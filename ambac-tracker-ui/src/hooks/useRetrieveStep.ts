import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type StepsResponse = Schema<"Steps">;

export const retrieveStepOptions = (queries: Parameters<typeof api.api_Steps_retrieve>[0]) => queryOptions({
    queryKey: ["step", queries] as const,
    queryFn: () => api.api_Steps_retrieve(queries) as Promise<StepsResponse>,
});

export function useRetrieveStep(queries: Parameters<typeof api.api_Steps_retrieve>[0], options?: { enabled?: boolean }){
    return useQuery({ ...retrieveStepOptions(queries), enabled: options?.enabled ?? true });
}