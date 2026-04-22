import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type BulkClearHoldVariables = {
    ids: string[];
};

export const useBulkClearHoldWorkOrders = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: BulkClearHoldVariables) =>
            api.api_WorkOrders_bulk_clear_hold_create(
                { ids: vars.ids },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" || q.queryKey[0] === "work-order",
            });
        },
    });
};
