import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type DeleteConfig = Parameters<typeof api.api_integrations_destroy>[1];
type DeleteParams = DeleteConfig["params"];

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const integrationsCatalogKeyOptions = () => ({ queryKey: ["integrations-catalog"] as const });
const integrationKeyOptions = () => ({ queryKey: ["integration"] as const });

export const useDeleteIntegration = () => {
    const queryClient = useQueryClient();

    return useMutation<unknown, unknown, { id: DeleteParams["id"] }>({
        mutationFn: ({ id }) =>
            api.api_integrations_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries(integrationsCatalogKeyOptions());
            queryClient.invalidateQueries(integrationKeyOptions());
        },
    });
};
