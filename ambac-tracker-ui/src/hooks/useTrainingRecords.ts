import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type TrainingRecordsListQueries = NonNullable<operations["api_TrainingRecords_list"]["parameters"]["query"]>;
type TrainingRecordsListResponse = components["schemas"]["PaginatedTrainingRecordList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useTrainingRecords(
  queries?: TrainingRecordsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<TrainingRecordsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<TrainingRecordsListResponse, Error>({
    queryKey: ["training-records", queries, config],
    queryFn: () =>
      api.api_TrainingRecords_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<TrainingRecordsListResponse>,
    ...options,
  });
}
