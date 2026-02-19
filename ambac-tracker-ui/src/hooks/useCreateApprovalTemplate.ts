import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type CreateInput = Parameters<typeof api.api_ApprovalTemplates_create>[0];
type CreateResponse = Awaited<ReturnType<typeof api.api_ApprovalTemplates_create>>;

export function useCreateApprovalTemplate() {
    const queryClient = useQueryClient();

    return useMutation<CreateResponse, unknown, CreateInput>({
        mutationFn: (data) =>
            api.api_ApprovalTemplates_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["approvalTemplates"] });
        },
    });
}
