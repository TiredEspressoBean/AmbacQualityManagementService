import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

export function useRetrieveDocumentTypes(
  queries?: Parameters<typeof api.api_DocumentTypes_list>[0],
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_DocumentTypes_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["document-type", queries],
    queryFn: () => api.api_DocumentTypes_list(queries),
    ...options,
  });
}
