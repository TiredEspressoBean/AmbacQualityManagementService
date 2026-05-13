import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

type RetrieveMeasurementDefinitionInput = Parameters<typeof api.api_MeasurementDefinitions_retrieve>[0];

export const retrieveMeasurementDefinitionOptions = (input: RetrieveMeasurementDefinitionInput) => queryOptions({
    queryKey: ["measurementDefinition", input] as const,
    queryFn: () => api.api_MeasurementDefinitions_retrieve(input),
});

export const useRetrieveMeasurementDefinition = (
    input: RetrieveMeasurementDefinitionInput,
    options?: Omit<ReturnType<typeof retrieveMeasurementDefinitionOptions>, "queryKey" | "queryFn">
) => {
    return useQuery({
        ...retrieveMeasurementDefinitionOptions(input),
        ...options,
    });
};
