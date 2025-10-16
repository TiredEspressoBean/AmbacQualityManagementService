import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils";

type UpdateHeatMapAnnotationInput = Parameters<typeof api.api_HeatMapAnnotation_partial_update>[0];
type UpdateHeatMapAnnotationConfig = Parameters<typeof api.api_HeatMapAnnotation_partial_update>[1];
type UpdateHeatMapAnnotationParams = UpdateHeatMapAnnotationConfig["params"];
type UpdateHeatMapAnnotationResponse = Awaited<ReturnType<typeof api.api_HeatMapAnnotation_partial_update>>;

type UpdateHeatMapAnnotationVariables = {
    id: UpdateHeatMapAnnotationParams["id"];
    data: UpdateHeatMapAnnotationInput;
};

export function useUpdateHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation<UpdateHeatMapAnnotationResponse, unknown, UpdateHeatMapAnnotationVariables>({
        mutationFn: ({ id, data }) =>
            api.api_HeatMapAnnotation_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
        },
    });
};
