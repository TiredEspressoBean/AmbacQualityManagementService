import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveStep(
    queries: Parameters<typeof api.api_Steps_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["step", queries],
        queryFn: () => api.api_Steps_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}