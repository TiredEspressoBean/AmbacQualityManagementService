import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateErrorTypeInput = Parameters<typeof api.api_Error_types_create>[0];

type CreateErrorResponse = Awaited<ReturnType<typeof api.api_Error_types_create>>;

export const useCreateErrorType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateErrorResponse, unknown, CreateErrorTypeInput>({
        mutationFn: (data) =>
            api.api_Error_types_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
