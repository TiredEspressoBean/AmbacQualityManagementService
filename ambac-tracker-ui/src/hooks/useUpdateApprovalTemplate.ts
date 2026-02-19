import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Infer types from the API
type UpdateInput = Parameters<typeof api.api_ApprovalTemplates_partial_update>[0];
type UpdateConfig = Parameters<typeof api.api_ApprovalTemplates_partial_update>[1];
type UpdateParams = UpdateConfig["params"];
type UpdateResponse = Awaited<ReturnType<typeof api.api_ApprovalTemplates_partial_update>>;

type UpdateVariables = {
    id: UpdateParams["id"];
    data: UpdateInput;
};

export function useUpdateApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation<UpdateResponse, unknown, UpdateVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ApprovalTemplates_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["approvalTemplates"] });
            queryClient.invalidateQueries({ queryKey: ["approvalTemplate", variables.id] });
        },
    });
}
