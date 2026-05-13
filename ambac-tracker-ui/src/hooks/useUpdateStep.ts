import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateStepInput = Schema<"PatchedStepsRequest">;
type UpdateStepResponse = Schema<"Steps">;

type UpdateStepVariables = {
    id: string;
    data: UpdateStepInput;
};

export const useUpdateStep = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateStepResponse, unknown, UpdateStepVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Steps_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateStepResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["step"],
                predicate: (query) => query.queryKey[0] === "step",
            });
        },
    });
};
