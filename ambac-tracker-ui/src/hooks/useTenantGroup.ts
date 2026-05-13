import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export const tenantGroupOptions = (id: string | undefined) => queryOptions({
    queryKey: ["tenantGroup", id] as const,
    queryFn: () => api.api_TenantGroups_retrieve({ params: { id: id! } }),
});

export function useTenantGroup(id: string | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        ...tenantGroupOptions(id),
        enabled: (options?.enabled ?? true) && !!id,
    });
}
