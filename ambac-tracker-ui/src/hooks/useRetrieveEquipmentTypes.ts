import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveEquipmentTypes(
  queries?: Parameters<typeof api.api_Equipment_types_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_Equipment_types_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["equipment-types", queries],
    queryFn: () => api.api_Equipment_types_list(queries),
    ...options,
  });
}