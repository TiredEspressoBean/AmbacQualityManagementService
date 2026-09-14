import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateErrorTypeInput = Schema<"PatchedQualityErrorsListRequest">;
type UpdateErrorTypeResponse = Schema<"QualityErrorsList">;

type UpdateErrorTypeVariables = {
    id: string;
    data: UpdateErrorTypeInput;
};

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const errorTypesInvalidateOptions = () => ({
    queryKey: ["error-types"] as const,
    predicate: (query: { queryKey: readonly unknown[] }) => query.queryKey[0] === "error-types",
});

export const useUpdateErrorType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateErrorTypeResponse, unknown, UpdateErrorTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Error_types_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateErrorTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(errorTypesInvalidateOptions());
        },
    });
};
