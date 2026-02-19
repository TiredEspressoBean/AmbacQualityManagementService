import { useQuery } from "@tanstack/react-query";
import type { TenantSettingsResponse } from "./useUpdateTenantSettings";

export function useTenantSettings(options?: { enabled?: boolean }) {
    return useQuery<TenantSettingsResponse>({
        queryKey: ["tenantSettings"],
        queryFn: async () => {
            const response = await fetch("/api/tenant/settings/", {
                credentials: "include",
            });
            if (!response.ok) {
                throw new Error("Failed to fetch tenant settings");
            }
            return response.json();
        },
        staleTime: 5 * 60 * 1000,
        enabled: options?.enabled ?? true,
    });
}
