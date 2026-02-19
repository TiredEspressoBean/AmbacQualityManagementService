import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useRetrieveMeasurementDefinitions(
  queries?: Parameters<typeof api.api_MeasurementDefinitions_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_MeasurementDefinitions_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["measurementDefinitions", queries],
    queryFn: () => api.api_MeasurementDefinitions_list(queries),
    ...options,
  });
}