import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateTrainingRecordInput = Schema<"PatchedTrainingRecordRequest">;
type UpdateTrainingRecordResponse = Schema<"TrainingRecord">;

type UpdateTrainingRecordVariables = {
    id: string;
    data: UpdateTrainingRecordInput;
};

export const useUpdateTrainingRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateTrainingRecordResponse, unknown, UpdateTrainingRecordVariables>({
        mutationFn: ({ id, data }) =>
            api.api_TrainingRecords_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateTrainingRecordResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["training-records"] });
            queryClient.invalidateQueries({ queryKey: ["training-record", variables.id] });
        },
    });
};
