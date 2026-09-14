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

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const approvalTemplatesKeyOptions = () => ({ queryKey: ["approvalTemplates"] as const });
const approvalTemplateKeyOptions = (id: string) => ({ queryKey: ["approvalTemplate", id] as const });

export function useUpdateApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation<UpdateResponse, unknown, UpdateVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ApprovalTemplates_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries(approvalTemplatesKeyOptions());
            queryClient.invalidateQueries(approvalTemplateKeyOptions(variables.id));
        },
    });
}
