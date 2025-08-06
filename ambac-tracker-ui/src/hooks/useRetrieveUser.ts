import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveUser(
    queries: Parameters<typeof api.api_User_retrieve>[0],
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["User", queries],
        queryFn: () => api.api_User_retrieve(queries),
        enabled: options?.enabled ?? true,
    });
}