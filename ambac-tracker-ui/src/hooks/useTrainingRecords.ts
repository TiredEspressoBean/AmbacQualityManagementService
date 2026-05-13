import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TrainingRecordsListQueries = NonNullable<operations["api_TrainingRecords_list"]["parameters"]["query"]>;
type TrainingRecordsListResponse = components["schemas"]["PaginatedTrainingRecordList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const trainingRecordsOptions = (queries?: TrainingRecordsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["training-records", queries, config] as const,
  queryFn: () =>
    api.api_TrainingRecords_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<TrainingRecordsListResponse>,
});

export function useTrainingRecords(
  queries?: TrainingRecordsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof trainingRecordsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...trainingRecordsOptions(queries, config),
    ...options,
  });
}
