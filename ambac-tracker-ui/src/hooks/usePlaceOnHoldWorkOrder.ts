import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type PlaceOnHoldVariables = {
    id: string;
    reason: string;
    notes?: string;
};

export const usePlaceOnHoldWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: PlaceOnHoldVariables) =>
            api.api_WorkOrders_place_on_hold_create(
                { reason: vars.reason, notes: vars.notes },
                {
                    params: { id: vars.id },
                    headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                },
            ),
        onSuccess: (_data, vars) => {
            queryClient.invalidateQueries({ queryKey: ["workorder", vars.id] });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "work-order",
            });
        },
    });
};
