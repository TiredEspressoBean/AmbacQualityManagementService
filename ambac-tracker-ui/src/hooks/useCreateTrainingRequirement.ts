import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateTrainingRequirementInput = Schema<"TrainingRequirementRequest">;
type CreateTrainingRequirementResponse = Schema<"TrainingRequirement">;

export const useCreateTrainingRequirement = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateTrainingRequirementResponse, unknown, CreateTrainingRequirementInput>({
        mutationFn: (data) =>
            api.api_TrainingRequirements_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateTrainingRequirementResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["training-requirements"] });
        },
    });
};
