import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

export const useBulkRollbackParts = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (ids: string[]) =>
            api.api_Parts_bulk_rollback_create(
                { ids },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
    });
};
