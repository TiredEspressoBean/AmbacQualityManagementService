import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateInput = Parameters<typeof api.api_integrations_partial_update>[0];
type UpdateConfig = Parameters<typeof api.api_integrations_partial_update>[1];
type UpdateParams = UpdateConfig["params"];
type UpdateResponse = Awaited<ReturnType<typeof api.api_integrations_partial_update>>;

type UpdateVariables = {
    id: UpdateParams["id"];
    data: UpdateInput;
};

export const useUpdateIntegration = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateResponse, unknown, UpdateVariables>({
        mutationFn: ({ id, data }) =>
            api.api_integrations_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ["integrations-catalog"] });
            queryClient.invalidateQueries({ queryKey: ["integration"] });
        },
    });
};
