import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type DocumentTypesListQueries = NonNullable<operations["api_DocumentTypes_list"]["parameters"]["query"]>;
type DocumentTypesListResponse = components["schemas"]["PaginatedDocumentTypeList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const documentTypesOptions = (queries?: DocumentTypesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["document-type", queries, config] as const,
    queryFn: () =>
      api.api_DocumentTypes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<DocumentTypesListResponse>,
  });

export const documentTypesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "DocumentTypes", "DocumentTypes"] as const,
    queryFn: () => api.api_DocumentTypes_metadata_retrieve(),
  });

export function useRetrieveDocumentTypes(
  queries?: DocumentTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof documentTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...documentTypesOptions(queries, config),
    ...options,
  });
}
