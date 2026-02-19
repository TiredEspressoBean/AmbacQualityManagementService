import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type UpdateInput = Parameters<typeof api.api_TrainingRecords_partial_update>[0];
type UpdateResponse = Awaited<ReturnType<typeof api.api_TrainingRecords_partial_update>>;

export const useUpdateTrainingRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateResponse, unknown, UpdateInput>({
        mutationFn: (data) =>
            api.api_TrainingRecords_partial_update(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["training-records"] });
            if (variables.params?.id) {
                queryClient.invalidateQueries({ queryKey: ["training-record", variables.params.id] });
            }
        },
    });
};
