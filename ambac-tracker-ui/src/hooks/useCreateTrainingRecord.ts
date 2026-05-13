import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateTrainingRecordInput = Schema<"TrainingRecordRequest">;
type CreateTrainingRecordResponse = Schema<"TrainingRecord">;

export const useCreateTrainingRecord = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateTrainingRecordResponse, unknown, CreateTrainingRecordInput>({
        mutationFn: (data) =>
            api.api_TrainingRecords_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateTrainingRecordResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["training-records"] });
        },
    });
};
