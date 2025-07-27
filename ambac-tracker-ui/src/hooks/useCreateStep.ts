import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateStepsInput = Parameters<typeof api.api_Steps_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_Steps_create>>;

export const useCreateStep = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreateStepsInput>({
        mutationFn: (data) =>
            api.api_Steps_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["step"] });
        },
    });
};
