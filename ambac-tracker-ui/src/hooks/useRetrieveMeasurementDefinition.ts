import { api } from "@/lib/api/generated";
import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

type RetrieveMeasurementDefinitionInput = Parameters<typeof api.api_MeasurementDefinitions_retrieve>[0];
type RetrieveMeasurementDefinitionResponse = Awaited<ReturnType<typeof api.api_MeasurementDefinitions_retrieve>>;

export const useRetrieveMeasurementDefinition = (
    input: RetrieveMeasurementDefinitionInput,
    options?: UseQueryOptions<RetrieveMeasurementDefinitionResponse>
) => {
    return useQuery<RetrieveMeasurementDefinitionResponse>({
        queryKey: ["measurementDefinition", input],
        queryFn: () => api.api_MeasurementDefinitions_retrieve(input),
        ...options,
    });
};