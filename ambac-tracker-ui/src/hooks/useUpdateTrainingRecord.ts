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
        // The form shows the server's reason itself; the global toast doubled it.
        meta: { suppressGlobalError: true },
        mutationFn: ({ id, data }) =>
            api.api_TrainingRecords_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateTrainingRecordResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "training-records" });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "training-record" && q.queryKey[1] === variables.id,
            });
        },
    });
};
