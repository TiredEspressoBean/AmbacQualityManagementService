import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type DocumentsListQueries = NonNullable<operations["api_Documents_list"]["parameters"]["query"]>;
type DocumentsListResponse = components["schemas"]["PaginatedDocumentsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveDocuments(
  queries?: DocumentsListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<DocumentsListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<DocumentsListResponse, Error>({
    queryKey: ["document", queries, config],
    queryFn: () =>
      api.api_Documents_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<DocumentsListResponse>,
    ...options,
  });
}
