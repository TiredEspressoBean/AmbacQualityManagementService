import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils";

type UpdateThreeDModelInput = Parameters<typeof api.api_ThreeDModels_partial_update>[0];
type UpdateThreeDModelConfig = Parameters<typeof api.api_ThreeDModels_partial_update>[1];
type UpdateThreeDModelParams = UpdateThreeDModelConfig["params"];
type UpdateThreeDModelResponse = Awaited<ReturnType<typeof api.api_ThreeDModels_partial_update>>;

type UpdateThreeDModelVariables = {
    id: UpdateThreeDModelParams["id"];
    data: UpdateThreeDModelInput;
};

export function useUpdateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<UpdateThreeDModelResponse, unknown, UpdateThreeDModelVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ThreeDModels_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threeDModel"] });
        },
    });
}
