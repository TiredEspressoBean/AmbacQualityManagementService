import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UndoSplitVariables = {
    id: string;
};

export const useUndoSplitWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: UndoSplitVariables) =>
            api.api_WorkOrders_undo_split_create(undefined, {
                params: { id: vars.id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" || q.queryKey[0] === "work-order",
            });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
    });
};
