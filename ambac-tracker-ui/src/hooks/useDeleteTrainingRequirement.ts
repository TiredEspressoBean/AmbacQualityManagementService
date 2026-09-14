import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const trainingRequirementsKeyOptions = () => ({ queryKey: ["training-requirements"] as const });

export const useDeleteTrainingRequirement = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_TrainingRequirements_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries(trainingRequirementsKeyOptions());
        },
    });
};
