import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRequestCapaApproval(capaId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () =>
            api.api_CAPAs_request_approval_create(undefined, { params: { id: capaId } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capas" });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "capa" && q.queryKey[1] === capaId,
            });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "approvals" });
        },
    });
}
