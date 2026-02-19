import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useTenantGroup(id: string | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        queryKey: ["tenantGroup", id],
        queryFn: () => api.api_TenantGroups_retrieve({ params: { id: id! } }),
        enabled: (options?.enabled ?? true) && !!id,
    });
}
