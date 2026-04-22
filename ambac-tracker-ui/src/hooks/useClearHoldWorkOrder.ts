import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type ClearHoldVariables = {
    id: string;
};

export const useClearHoldWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: ClearHoldVariables) =>
            api.api_WorkOrders_clear_hold_create(undefined, {
                params: { id: vars.id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: (_data, vars) => {
            queryClient.invalidateQueries({ queryKey: ["workorder", vars.id] });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "work-order",
            });
        },
    });
};
