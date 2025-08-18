import { api } from "@/lib/api/generated";
import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

type RetrieveMeasurementDefinitionsInput = Parameters<typeof api.api_MeasurementDefinitions_list>[0];
type RetrieveMeasurementDefinitionsResponse = Awaited<ReturnType<typeof api.api_MeasurementDefinitions_list>>;

export const useRetrieveMeasurementDefinitions = (
    input?: RetrieveMeasurementDefinitionsInput,
    options?: UseQueryOptions<RetrieveMeasurementDefinitionsResponse>
) => {
    return useQuery<RetrieveMeasurementDefinitionsResponse>({
        queryKey: ["measurementDefinitions", input],
        queryFn: () => api.api_MeasurementDefinitions_list(input || {}),
        ...options,
    });
};