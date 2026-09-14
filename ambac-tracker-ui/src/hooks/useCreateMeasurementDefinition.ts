import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateMeasurementDefinitionInput = Schema<"MeasurementDefinitionRequest">;
type CreateMeasurementDefinitionResponse = Schema<"MeasurementDefinition">;

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const measurementDefinitionKeyOptions = () => ({ queryKey: ["measurementDefinition"] as const });
const measurementDefinitionsKeyOptions = () => ({ queryKey: ["measurementDefinitions"] as const });

export const useCreateMeasurementDefinition = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateMeasurementDefinitionResponse, unknown, CreateMeasurementDefinitionInput>({
        mutationFn: (data) =>
            api.api_MeasurementDefinitions_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateMeasurementDefinitionResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(measurementDefinitionKeyOptions());
            queryClient.invalidateQueries(measurementDefinitionsKeyOptions());
        },
    });
};
