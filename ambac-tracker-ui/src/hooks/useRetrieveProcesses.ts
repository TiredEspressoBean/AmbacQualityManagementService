import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type ProcessesListQueries = NonNullable<operations["api_Processes_list"]["parameters"]["query"]>;
type ProcessesListResponse = components["schemas"]["PaginatedProcessesList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useRetrieveProcesses(
  queries?: ProcessesListQueries,
  config?: ListHookConfig,
  options?: Omit<
    UseQueryOptions<ProcessesListResponse, Error>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<ProcessesListResponse, Error>({
    queryKey: ["process", queries, config],
    queryFn: () =>
      api.api_Processes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ProcessesListResponse>,
    ...options,
  });
}
