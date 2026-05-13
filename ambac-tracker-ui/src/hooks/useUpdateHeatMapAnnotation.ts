import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateHeatMapAnnotationInput = Schema<"PatchedHeatMapAnnotationsRequest">;
type UpdateHeatMapAnnotationResponse = Schema<"HeatMapAnnotations">;

type UpdateHeatMapAnnotationVariables = {
    id: string;
    data: UpdateHeatMapAnnotationInput;
};

export function useUpdateHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation<UpdateHeatMapAnnotationResponse, unknown, UpdateHeatMapAnnotationVariables>({
        mutationFn: ({ id, data }) =>
            api.api_HeatMapAnnotation_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateHeatMapAnnotationResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
        },
    });
}
