import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveProcess(
    queries: Parameters<typeof api.api_Processes_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["process", queries],
        queryFn: () => api.api_Processes_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}