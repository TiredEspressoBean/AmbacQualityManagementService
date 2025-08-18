import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateMeasurementDefinitionInput = Parameters<typeof api.api_MeasurementDefinitions_create>[0];
type CreateMeasurementDefinitionResponse = Awaited<ReturnType<typeof api.api_MeasurementDefinitions_create>>;

export const useCreateMeasurementDefinition = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateMeasurementDefinitionResponse, unknown, CreateMeasurementDefinitionInput>({
        mutationFn: (data) =>
            api.api_MeasurementDefinitions_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["measurementDefinition"] });
            queryClient.invalidateQueries({ queryKey: ["measurementDefinitions"] });
        },
    });
};