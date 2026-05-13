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

export const useUpdateErrorType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateErrorTypeResponse, unknown, UpdateErrorTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Error_types_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateErrorTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["error-types"],
                predicate: (query) => query.queryKey[0] === "error-types",
            });
        },
    });
};
