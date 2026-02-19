import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveHeatMapAnnotations(
  queries?: Parameters<typeof api.api_HeatMapAnnotation_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_HeatMapAnnotation_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["heatMapAnnotation", queries],
    queryFn: () => api.api_HeatMapAnnotation_list(queries),
    ...options,
  });
}
