import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export function useUploadTenantLogo() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (file: File) =>
            api.api_tenant_logo_create(
                { logo: file },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "tenant" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "tenantSettings" });
        },
    });
}

export function useDeleteTenantLogo() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () =>
            api.api_tenant_logo_destroy(undefined, {
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "tenant" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "tenantSettings" });
        },
    });
}
