import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveContentTypes(
  queries?: Parameters<typeof api.api_content_types_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_content_types_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["contentTypes", queries],
    queryFn: () => api.api_content_types_list(queries),
    ...options,
  });
}