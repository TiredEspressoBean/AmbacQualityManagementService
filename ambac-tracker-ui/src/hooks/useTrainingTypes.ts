import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TrainingTypesListQueries = NonNullable<operations["api_TrainingTypes_list"]["parameters"]["query"]>;
type TrainingTypesListResponse = components["schemas"]["PaginatedTrainingTypeList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useTrainingTypes(
  queries?: TrainingTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<TrainingTypesListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<TrainingTypesListResponse, Error>({
    queryKey: ["training-types", queries, config],
    queryFn: () =>
      api.api_TrainingTypes_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<TrainingTypesListResponse>,
    ...options,
  });
}
