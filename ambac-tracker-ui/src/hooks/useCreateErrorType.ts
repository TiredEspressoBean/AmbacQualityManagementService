import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateErrorTypeInput = Schema<"QualityErrorsListRequest">;
type CreateErrorTypeResponse = Schema<"QualityErrorsList">;

export const useCreateErrorType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateErrorTypeResponse, unknown, CreateErrorTypeInput>({
        mutationFn: (data) =>
            api.api_Error_types_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateErrorTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
