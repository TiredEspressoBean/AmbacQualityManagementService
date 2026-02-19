import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveEquipments(
  queries?: Parameters<typeof api.api_Equipment_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Equipment_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["equipment", queries],
    queryFn: () => api.api_Equipment_list(queries),
    ...options,
  });
}