import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type PlaceOnHoldVariables = {
    id: string;
    reason: string;
    notes?: string;
};

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const workorderKeyOptions = (id: string) => ({ queryKey: ["workorder", id] as const });

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
            queryClient.invalidateQueries(workorderKeyOptions(vars.id));
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "work-order",
            });
        },
    });
};
