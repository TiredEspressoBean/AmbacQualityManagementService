import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRequestCapaApproval(capaId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () =>
            api.api_CAPAs_request_approval_create({ id: capaId }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capas"] });
            queryClient.invalidateQueries({ queryKey: ["capa", capaId] });
            queryClient.invalidateQueries({ queryKey: ["approvals"] });
        },
    });
}
