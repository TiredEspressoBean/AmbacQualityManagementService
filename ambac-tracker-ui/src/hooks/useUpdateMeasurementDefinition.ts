import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type UpdateMeasurementDefinitionInput = Parameters<typeof api.api_MeasurementDefinitions_update>[0];
type UpdateMeasurementDefinitionResponse = Awaited<ReturnType<typeof api.api_MeasurementDefinitions_update>>;

export const useUpdateMeasurementDefinition = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateMeasurementDefinitionResponse, unknown, UpdateMeasurementDefinitionInput>({
        mutationFn: (data) =>
            api.api_MeasurementDefinitions_update(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["measurementDefinition"] });
            queryClient.invalidateQueries({ queryKey: ["measurementDefinitions"] });
        },
    });
};