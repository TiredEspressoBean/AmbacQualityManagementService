import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

export const useDeleteTrainingRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<void, unknown, { id: string }>({
        mutationFn: ({ id }) =>
            api.api_TrainingRecords_destroy(
                { params: { id } },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["training-records"] });
        },
    });
};
