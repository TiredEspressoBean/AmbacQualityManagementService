import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export const useDeleteTrainingType = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_TrainingTypes_destroy(
                { params: { id } },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["training-types"] });
        },
    });
};
