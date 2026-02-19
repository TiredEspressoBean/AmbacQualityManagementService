// src/hooks/useTenant.ts
import { useQuery } from "@tanstack/react-query";
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
export function useTenant(options?: { enabled?: boolean }) {
    return useQuery({
        queryKey: ["tenant", "current"],
        queryFn: () => api.api_tenant_current_retrieve() as Promise<CurrentTenantResponse>,
        staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
        retry: 1,
        enabled: options?.enabled ?? true,
    });
}

// Convenience type exports
export type { CurrentTenantResponse, TenantInfo, DeploymentInfo } from "@/lib/api/generated";
