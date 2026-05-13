import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateHeatMapAnnotationInput = Schema<"HeatMapAnnotationsRequest">;
type CreateHeatMapAnnotationResponse = Schema<"HeatMapAnnotations">;

export function useCreateHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation<CreateHeatMapAnnotationResponse, unknown, CreateHeatMapAnnotationInput>({
        mutationFn: (data) =>
            api.api_HeatMapAnnotation_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateHeatMapAnnotationResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
        },
    });
}
