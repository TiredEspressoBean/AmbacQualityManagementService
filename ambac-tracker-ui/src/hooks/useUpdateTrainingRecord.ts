import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateTrainingRecordInput = Parameters<typeof api.api_TrainingRecords_partial_update>[0];
type UpdateTrainingRecordConfig = Parameters<typeof api.api_TrainingRecords_partial_update>[1];
type UpdateTrainingRecordParams = UpdateTrainingRecordConfig["params"];
type UpdateTrainingRecordResponse = Awaited<ReturnType<typeof api.api_TrainingRecords_partial_update>>;

type UpdateTrainingRecordVariables = {
    id: UpdateTrainingRecordParams["id"];
    data: UpdateTrainingRecordInput;
};

export const useUpdateTrainingRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateTrainingRecordResponse, unknown, UpdateTrainingRecordVariables>({
        mutationFn: ({ id, data }) =>
            api.api_TrainingRecords_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["training-records"] });
            queryClient.invalidateQueries({ queryKey: ["training-record", variables.id] });
        },
    });
};
