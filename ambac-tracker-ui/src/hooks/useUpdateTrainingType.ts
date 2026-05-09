import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type UpdateTrainingTypeInput = Parameters<typeof api.api_TrainingTypes_partial_update>[0];
type UpdateTrainingTypeConfig = Parameters<typeof api.api_TrainingTypes_partial_update>[1];
type UpdateTrainingTypeParams = UpdateTrainingTypeConfig["params"];
type UpdateTrainingTypeResponse = Awaited<ReturnType<typeof api.api_TrainingTypes_partial_update>>;

type UpdateTrainingTypeVariables = {
    id: UpdateTrainingTypeParams["id"];
    data: UpdateTrainingTypeInput;
};

export const useUpdateTrainingType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateTrainingTypeResponse, unknown, UpdateTrainingTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_TrainingTypes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["training-types"] });
            queryClient.invalidateQueries({ queryKey: ["training-type", variables.id] });
        },
    });
};
