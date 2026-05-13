import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type DocumentsListQueries = NonNullable<operations["api_Documents_list"]["parameters"]["query"]>;
type DocumentsListResponse = components["schemas"]["PaginatedDocumentsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const documentsOptions = (queries?: DocumentsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["document", queries, config] as const,
    queryFn: () =>
      api.api_Documents_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<DocumentsListResponse>,
  });

export const documentsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Documents", "Documents"] as const,
    queryFn: () => api.api_Documents_metadata_retrieve(),
  });

export function useRetrieveDocuments(
  queries?: DocumentsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof documentsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...documentsOptions(queries, config),
    ...options,
  });
}
