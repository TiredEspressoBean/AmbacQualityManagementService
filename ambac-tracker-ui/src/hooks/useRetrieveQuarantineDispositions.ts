import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveQuarantineDispositions(
  queries?: Parameters<typeof api.api_QuarantineDispositions_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_QuarantineDispositions_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["quarantine-disposition", queries],
    queryFn: () => api.api_QuarantineDispositions_list(queries),
    ...options,
  });
}