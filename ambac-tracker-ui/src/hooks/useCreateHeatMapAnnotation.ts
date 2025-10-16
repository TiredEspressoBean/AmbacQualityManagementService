import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils";

type CreateHeatMapAnnotationInput = Parameters<typeof api.api_HeatMapAnnotation_create>[0];
type CreateHeatMapAnnotationResponse = Awaited<ReturnType<typeof api.api_HeatMapAnnotation_create>>;

export function useCreateHeatMapAnnotation() {
    const queryClient = useQueryClient();

    return useMutation<CreateHeatMapAnnotationResponse, unknown, CreateHeatMapAnnotationInput>({
        mutationFn: (data) =>
            api.api_HeatMapAnnotation_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["heatMapAnnotation"] });
        },
    });
};
