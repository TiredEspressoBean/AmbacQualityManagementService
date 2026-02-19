import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export type TenantSettingsUpdate = {
    name?: string;
    contact_email?: string;
    contact_phone?: string;
    website?: string;
    address?: string;
    default_timezone?: string;
    settings?: Record<string, unknown>;
};

export type TenantSettingsResponse = {
    name: string;
    tier: string;
    status: string;
    settings: Record<string, unknown>;
    contact_email: string;
    contact_phone: string;
    website: string;
    address: string;
    default_timezone: string;
    logo_url: string | null;
};

export function useUpdateTenantSettings() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: TenantSettingsUpdate): Promise<TenantSettingsResponse> => {
            const response = await fetch("/api/tenant/settings/", {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                credentials: "include",
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || "Failed to update tenant settings");
            }
            return response.json();
        },
        onSuccess: () => {
            // Invalidate all tenant-related queries to refresh branding
            queryClient.invalidateQueries({ queryKey: ["tenant", "current"] });
            queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
        },
    });
}
