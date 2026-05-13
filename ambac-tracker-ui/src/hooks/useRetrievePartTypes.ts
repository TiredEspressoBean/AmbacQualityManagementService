import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type PartTypesListQueries = NonNullable<operations["api_PartTypes_list"]["parameters"]["query"]>;
type PartTypesListResponse = components["schemas"]["PaginatedPartTypesList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const partTypesOptions = (queries?: PartTypesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["part-type", queries, config] as const,
    queryFn: () =>
      api.api_PartTypes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<PartTypesListResponse>,
  });

export const partTypesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "PartTypes", "PartTypes"] as const,
    queryFn: () => api.api_PartTypes_metadata_retrieve(),
  });

export function useRetrievePartTypes(
  queries?: PartTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof partTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...partTypesOptions(queries, config),
    ...options,
  });
}
