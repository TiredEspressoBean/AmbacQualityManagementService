import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type DeleteConfig = Parameters<typeof api.api_integrations_destroy>[1];
type DeleteParams = DeleteConfig["params"];

export const useDeleteIntegration = () => {
    const queryClient = useQueryClient();

    return useMutation<unknown, unknown, { id: DeleteParams["id"] }>({
        mutationFn: ({ id }) =>
            api.api_integrations_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["integrations-catalog"] });
            queryClient.invalidateQueries({ queryKey: ["integration"] });
        },
    });
};
