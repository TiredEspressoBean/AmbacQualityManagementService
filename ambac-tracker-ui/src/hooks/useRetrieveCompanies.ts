import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

type CompaniesListQueries = NonNullable<operations["api_Companies_list"]["parameters"]["query"]>;
type CompaniesListResponse = components["schemas"]["PaginatedCompanyList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveCompanies(
  queries?: CompaniesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<CompaniesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<CompaniesListResponse, Error>({
    queryKey: ["company", queries, config],
    queryFn: () =>
      api.api_Companies_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CompaniesListResponse>,
    ...options,
  });
}
