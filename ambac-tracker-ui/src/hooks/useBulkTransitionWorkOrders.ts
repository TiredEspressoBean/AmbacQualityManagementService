import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { WorkOrderStatusEnum } from "@/lib/api/generated";

type BulkTransitionVariables = {
    ids: string[];
    status: WorkOrderStatusEnum;
    notes?: string;
};

export const useBulkTransitionWorkOrders = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: BulkTransitionVariables) =>
            api.api_WorkOrders_bulk_transition_create(
                { ids: vars.ids, status: vars.status, notes: vars.notes },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" || q.queryKey[0] === "work-order",
            });
        },
    });
};
