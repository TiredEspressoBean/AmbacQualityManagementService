import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type CalibrationRecordsListQueries = NonNullable<operations["api_CalibrationRecords_list"]["parameters"]["query"]>;
type CalibrationRecordsListResponse = components["schemas"]["PaginatedCalibrationRecordList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useCalibrationRecords(
  queries?: CalibrationRecordsListQueries,
  config?: ListHookConfig,
  options?: Omit<UseQueryOptions<CalibrationRecordsListResponse, Error>, "queryKey" | "queryFn">
) {
  return useQuery<CalibrationRecordsListResponse, Error>({
    queryKey: ["calibration-records", queries, config],
    queryFn: () =>
      api.api_CalibrationRecords_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<CalibrationRecordsListResponse>,
    ...options,
  });
}
