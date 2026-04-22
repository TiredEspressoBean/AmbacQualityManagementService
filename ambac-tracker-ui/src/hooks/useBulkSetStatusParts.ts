import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type BulkSetStatusVariables = {
    ids: string[];
    status: string;
    reason?: string;
};

export const useBulkSetStatusParts = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: BulkSetStatusVariables) =>
            api.api_Parts_bulk_set_status_create(
                { ids: payload.ids, status: payload.status as never, reason: payload.reason },
                { headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "parts",
            });
        },
    });
};
