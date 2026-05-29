import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { PartsStatusEnum } from "@/lib/api/generated";

type BulkAddPartsVariables = {
    workOrderId: string;
    part_type: string;
    step: string;
    quantity: number;
    erp_id_start?: number;
    part_status?: PartsStatusEnum;
};

export const useBulkAddPartsToWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ workOrderId, ...body }: BulkAddPartsVariables) =>
            api.api_WorkOrders_bulk_add_parts_create(
                body,
                {
                    params: { id: workOrderId },
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) =>
                    q.queryKey[0] === "workorder" ||
                    q.queryKey[0] === "work-order" ||
                    q.queryKey[0] === "part" ||
                    q.queryKey[0] === "parts",
            });
        },
    });
};