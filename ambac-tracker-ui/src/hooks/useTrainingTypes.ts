import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TrainingTypesListQueries = NonNullable<operations["api_TrainingTypes_list"]["parameters"]["query"]>;
type TrainingTypesListResponse = components["schemas"]["PaginatedTrainingTypeList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const trainingTypesOptions = (queries?: TrainingTypesListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["training-types", queries, config] as const,
  queryFn: () =>
    api.api_TrainingTypes_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<TrainingTypesListResponse>,
});

export function useTrainingTypes(
  queries?: TrainingTypesListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof trainingTypesOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...trainingTypesOptions(queries, config),
    ...options,
  });
}
