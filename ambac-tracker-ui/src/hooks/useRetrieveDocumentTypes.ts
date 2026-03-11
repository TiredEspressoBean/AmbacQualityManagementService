import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";

// Extract queries type from Zodios endpoint
type DocumentTypesListQueries = Parameters<typeof api.api_DocumentTypes_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_DocumentTypes_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveDocumentTypes(
  queries?: DocumentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof api.api_DocumentTypes_list>>,
      Error
    >,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: ["document-type", queries, config],
    queryFn: () => api.api_DocumentTypes_list(queries || config ? { queries, ...config } : undefined),
    ...options,
  });
}
