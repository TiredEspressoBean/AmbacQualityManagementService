import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateInput = Schema<"PatchedApprovalTemplateRequest">;
type UpdateResponse = Schema<"ApprovalTemplate">;

type UpdateVariables = {
    id: string;
    data: UpdateInput;
};

export function useUpdateApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation<UpdateResponse, unknown, UpdateVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ApprovalTemplates_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["approvalTemplates"] });
            queryClient.invalidateQueries({ queryKey: ["approvalTemplate", variables.id] });
        },
    });
}
