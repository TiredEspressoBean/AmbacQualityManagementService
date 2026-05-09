import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type StepsResponse = Schema<"Steps">;

export function useRetrieveStep(
    queries: Parameters<typeof api.api_Steps_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery<StepsResponse>({
        queryKey: ["step", queries],
        queryFn: () => api.api_Steps_retrieve(queries) as Promise<StepsResponse>,
        enabled: options?.enabled ?? true,
    });
}