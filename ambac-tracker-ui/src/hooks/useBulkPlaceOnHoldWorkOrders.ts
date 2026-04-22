import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type BulkPlaceOnHoldVariables = {
    ids: string[];
    reason: string;
    notes?: string;
};

export const useBulkPlaceOnHoldWorkOrders = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: BulkPlaceOnHoldVariables) =>
            api.api_WorkOrders_bulk_place_on_hold_create(
                { ids: vars.ids, reason: vars.reason, notes: vars.notes },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" || q.queryKey[0] === "work-order",
            });
        },
    });
};
