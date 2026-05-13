import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateTrainingTypeInput = Schema<"TrainingTypeRequest">;
type CreateTrainingTypeResponse = Schema<"TrainingType">;

export const useCreateTrainingType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateTrainingTypeResponse, unknown, CreateTrainingTypeInput>({
        mutationFn: (data) =>
            api.api_TrainingTypes_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateTrainingTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["training-types"] });
        },
    });
};
