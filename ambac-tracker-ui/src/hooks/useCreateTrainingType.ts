import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateTrainingTypeInput = Schema<"TrainingTypeRequest">;
type CreateTrainingTypeResponse = Schema<"TrainingType">;

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const trainingTypesKeyOptions = () => ({ queryKey: ["training-types"] as const });

export const useCreateTrainingType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateTrainingTypeResponse, unknown, CreateTrainingTypeInput>({
        mutationFn: (data) =>
            api.api_TrainingTypes_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateTrainingTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(trainingTypesKeyOptions());
        },
    });
};
