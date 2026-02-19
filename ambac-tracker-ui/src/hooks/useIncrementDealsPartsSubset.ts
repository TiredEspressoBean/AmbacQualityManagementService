import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils.ts";

export function usePartsIncrementMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ orderId, stepId }: { orderId: string; stepId: string }) =>
            api.api_Orders_increment_step_create(
                { order_id: orderId, step_id: stepId },
                {
                    params: { id: orderId },
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                }
            ),
        onSuccess: (_, { orderId }) => {
            queryClient.invalidateQueries({ queryKey: ['step-distribution', orderId] });
        },
    });
}
