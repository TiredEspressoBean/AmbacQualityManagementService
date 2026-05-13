import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CompaniesListQueries = NonNullable<operations["api_Companies_list"]["parameters"]["query"]>;
type CompaniesListResponse = components["schemas"]["PaginatedCompanyList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const companiesOptions = (queries?: CompaniesListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["company", queries, config] as const,
    queryFn: () =>
      api.api_Companies_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CompaniesListResponse>,
  });

export const companiesMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Companies", "Companies"] as const,
    queryFn: () => api.api_Companies_metadata_retrieve(),
  });

export function useRetrieveCompanies(
  queries?: CompaniesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof companiesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...companiesOptions(queries, config),
    ...options,
  });
}
