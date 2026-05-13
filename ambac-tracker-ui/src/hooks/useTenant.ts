// src/hooks/useTenant.ts
import { useQuery, queryOptions } from "@tanstack/react-query";
import { api, type CurrentTenantResponse } from "@/lib/api/generated";

/**
 * Fetches current tenant information and deployment mode.
 *
 * Used by the frontend to:
 * - Determine which UI elements to show based on deployment mode
 * - Get tenant branding (logo, colors)
 * - Check feature flags and limits
 * - Display tenant name in header
 *
 * Authentication is optional - unauthenticated requests get deployment info only.
 */
export const tenantOptions = () => queryOptions({
    queryKey: ["tenant", "current"] as const,
    queryFn: () => api.api_tenant_current_retrieve() as Promise<CurrentTenantResponse>,
});

export function useTenant(options?: { enabled?: boolean }){
    return useQuery({ ...tenantOptions(), enabled: options?.enabled ?? true, retry: 1, staleTime: 5 * 60 * 1000 });
}

// Convenience type exports
export type { CurrentTenantResponse, TenantInfo, DeploymentInfo } from "@/lib/api/generated";
