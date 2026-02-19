import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export function useUploadTenantLogo() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (file: File): Promise<{ logo_url: string | null }> => {
            const formData = new FormData();
            formData.append("logo", file);

            const response = await fetch("/api/tenant/logo/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                credentials: "include",
                body: formData,
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || "Failed to upload logo");
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenant"] });
            queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
        },
    });
}

export function useDeleteTenantLogo() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (): Promise<{ logo_url: null }> => {
            const response = await fetch("/api/tenant/logo/", {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                credentials: "include",
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || "Failed to delete logo");
            }
            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenant"] });
            queryClient.invalidateQueries({ queryKey: ["tenantSettings"] });
        },
    });
}
