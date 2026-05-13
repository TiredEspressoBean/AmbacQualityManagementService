import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRequestCapaApproval(capaId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () =>
            // eslint-disable-next-line local/no-as-any -- api_CAPAs_request_approval_create requires a body but this action has none; passing empty object
            api.api_CAPAs_request_approval_create({} as any, { params: { id: capaId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capas"] });
            queryClient.invalidateQueries({ queryKey: ["capa", capaId] });
            queryClient.invalidateQueries({ queryKey: ["approvals"] });
        },
    });
}
