import { useMutation, useQueryClient, type UseMutationOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type RemovePartsResult = Awaited<ReturnType<typeof api.api_Orders_parts_bulk_remove_create>>;

interface UseRemovePartsMutationArgs {
    orderId: number;
    invalidateQueryKeys?: Array<string | unknown[]>;
}

export function useRemovePartsMutation(
    { orderId, invalidateQueryKeys }: UseRemovePartsMutationArgs,
    options?: UseMutationOptions<RemovePartsResult, unknown, number[]>
) {
    const queryClient = useQueryClient();

    return useMutation<RemovePartsResult, unknown, number[]>({
        mutationFn: (ids) =>
            api.api_Orders_parts_bulk_remove_create(
                { ids },
                {
                    params: { id: orderId },
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken") ?? "",
                    },
                }
            ),
        onSuccess: (data, ...rest) => {
            invalidateQueryKeys?.forEach((key) => {
                const queryKey = typeof key === "string" ? [key] : key;
                queryClient.invalidateQueries({ queryKey });
            });
            options?.onSuccess?.(data, ...rest);
        },
        ...options,
    });
}
