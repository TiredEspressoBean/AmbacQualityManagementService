import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateTrainingTypeInput = Schema<"PatchedTrainingTypeRequest">;
type UpdateTrainingTypeResponse = Schema<"TrainingType">;

type UpdateTrainingTypeVariables = {
    id: string;
    data: UpdateTrainingTypeInput;
};

export const useUpdateTrainingType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateTrainingTypeResponse, unknown, UpdateTrainingTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_TrainingTypes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateTrainingTypeResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "training-types" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "training-type" && q.queryKey[1] === variables.id });
        },
    });
};
