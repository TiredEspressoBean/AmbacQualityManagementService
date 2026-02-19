import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useListHubspotGates(
  queries?: Parameters<typeof api.api_HubspotGates_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_HubspotGates_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["hubspotGates", queries],
    queryFn: () => api.api_HubspotGates_list(queries),
    ...options,
  });
}