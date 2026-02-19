import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useListCapas(
  queries?: Parameters<typeof api.api_CAPAs_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_CAPAs_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["capas", queries],
    queryFn: () => api.api_CAPAs_list(queries),
    ...options,
  });
}