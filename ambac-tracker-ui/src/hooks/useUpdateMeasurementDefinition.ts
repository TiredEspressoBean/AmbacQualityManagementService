import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateMeasurementDefinitionInput = Schema<"MeasurementDefinitionRequest">;
type UpdateMeasurementDefinitionResponse = Schema<"MeasurementDefinition">;
type UpdateMeasurementDefinitionVariables = {
    id: string;
    data: UpdateMeasurementDefinitionInput;
};

export const useUpdateMeasurementDefinition = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateMeasurementDefinitionResponse, unknown, UpdateMeasurementDefinitionVariables>({
        mutationFn: ({ id, data }) =>
            api.api_MeasurementDefinitions_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateMeasurementDefinitionResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["measurementDefinition"] });
            queryClient.invalidateQueries({ queryKey: ["measurementDefinitions"] });
        },
    });
};
