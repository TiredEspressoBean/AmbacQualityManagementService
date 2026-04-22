import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type SplitWorkOrderVariables = {
    id: string;
    reason: string;
    new_erp_id: string;
    part_ids?: string[];
    quantity?: number;
    target_process_id?: string | null;
    notes?: string;
};

export const useSplitWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, ...body }: SplitWorkOrderVariables) =>
            api.api_WorkOrders_split_create(body as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: (_data, vars) => {
            queryClient.invalidateQueries({ queryKey: ["workorder", vars.id] });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" || q.queryKey[0] === "work-order",
            });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
    });
};
