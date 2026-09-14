import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, schemas } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { z } from "zod";

export type TenantSettingsUpdate = z.infer<typeof schemas.PatchedTenantSettingsUpdateRequestRequest>;
export type TenantSettingsResponse = Awaited<ReturnType<typeof api.api_tenant_settings_partial_update>>;

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const tenantCurrentKeyOptions = () => ({ queryKey: ["tenant", "current"] as const });
const tenantSettingsKeyOptions = () => ({ queryKey: ["tenantSettings"] as const });

export function useUpdateTenantSettings() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: TenantSettingsUpdate) =>
            api.api_tenant_settings_partial_update(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            // Invalidate all tenant-related queries to refresh branding
            queryClient.invalidateQueries(tenantCurrentKeyOptions());
            queryClient.invalidateQueries(tenantSettingsKeyOptions());
        },
    });
}
