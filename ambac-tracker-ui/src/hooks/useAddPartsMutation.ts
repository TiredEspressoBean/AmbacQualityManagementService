import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

type AddPartsBody = Parameters<typeof api.api_Orders_parts_bulk_add_create>[0];
type AddPartsResult = Awaited<ReturnType<typeof api.api_Orders_parts_bulk_add_create>>;

export function useAddPartsMutation(
    id: string,
    options?: UseMutationOptions<AddPartsResult, unknown, AddPartsBody>
) {
    return useMutation<AddPartsResult, unknown, AddPartsBody>({
        mutationFn: (data) =>
            api.api_Orders_parts_bulk_add_create(data, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),
        ...options,
    });
}
