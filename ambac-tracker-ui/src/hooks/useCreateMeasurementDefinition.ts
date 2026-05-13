import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateMeasurementDefinitionInput = Schema<"MeasurementDefinitionRequest">;
type CreateMeasurementDefinitionResponse = Schema<"MeasurementDefinition">;

export const useCreateMeasurementDefinition = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateMeasurementDefinitionResponse, unknown, CreateMeasurementDefinitionInput>({
        mutationFn: (data) =>
            api.api_MeasurementDefinitions_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateMeasurementDefinitionResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["measurementDefinition"] });
            queryClient.invalidateQueries({ queryKey: ["measurementDefinitions"] });
        },
    });
};
