import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveHarvestedComponents(
  queries?: Parameters<typeof api.api_HarvestedComponents_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_HarvestedComponents_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["harvested-components", queries],
    queryFn: () => api.api_HarvestedComponents_list(queries),
    ...options,
  });
}
