import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateInput = Schema<"ApprovalTemplateRequest">;
type CreateResponse = Schema<"ApprovalTemplate">;

export function useCreateApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation<CreateResponse, unknown, CreateInput>({
        mutationFn: (data) =>
            api.api_ApprovalTemplates_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["approvalTemplates"] });
        },
    });
}
