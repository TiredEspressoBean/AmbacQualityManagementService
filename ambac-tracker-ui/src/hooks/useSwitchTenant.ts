import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

/**
 * Switch to a different tenant.
 * This updates the session to use the new tenant context.
 */
export function useSwitchTenant() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (tenantId: string): Promise<void> => {
            const response = await fetch("/api/user/tenants/switch/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                credentials: "include",
                body: JSON.stringify({ tenant_id: tenantId }),
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || "Failed to switch tenant");
            }
        },
        onSuccess: () => {
            // Invalidate all queries to refresh data for new tenant
            queryClient.invalidateQueries();
            // Reload the page to ensure clean state
            window.location.href = "/";
        },
    });
}
