import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateStepInput = Schema<"StepsRequest">;
type CreateStepResponse = Schema<"Steps">;

export const useCreateStep = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateStepResponse, unknown, CreateStepInput>({
        mutationFn: (data) =>
            api.api_Steps_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateStepResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["step"] });
        },
    });
};
