import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

/**
 * Switch to a different tenant.
 * This updates the session to use the new tenant context.
 */
export function useSwitchTenant() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (tenantId: string) =>
            api.api_user_tenants_switch_create(
                { tenant_id: tenantId },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } }
            ),
        onSuccess: () => {
            // Invalidate all queries to refresh data for new tenant
            queryClient.invalidateQueries();
            // Reload the page to ensure clean state
            window.location.href = "/";
        },
    });
}
