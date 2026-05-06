import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type DocumentTypesListQueries = NonNullable<operations["api_DocumentTypes_list"]["parameters"]["query"]>;
type DocumentTypesListResponse = components["schemas"]["PaginatedDocumentTypeList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveDocumentTypes(
  queries?: DocumentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<DocumentTypesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<DocumentTypesListResponse, Error>({
    queryKey: ["document-type", queries, config],
    queryFn: () =>
      api.api_DocumentTypes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<DocumentTypesListResponse>,
    ...options,
  });
}
