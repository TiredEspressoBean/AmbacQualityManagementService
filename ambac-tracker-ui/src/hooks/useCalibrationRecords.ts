import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type CalibrationRecordsListQueries = NonNullable<operations["api_CalibrationRecords_list"]["parameters"]["query"]>;
type CalibrationRecordsListResponse = components["schemas"]["PaginatedCalibrationRecordList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const calibrationRecordsOptions = (queries?: CalibrationRecordsListQueries, config?: ListHookConfig) => queryOptions({
  queryKey: ["calibration-records", queries, config] as const,
  queryFn: () =>
    api.api_CalibrationRecords_list(
      (queries || config ? { queries, ...config } : undefined) as never,
    ) as Promise<CalibrationRecordsListResponse>,
});

export function useCalibrationRecords(
  queries?: CalibrationRecordsListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof calibrationRecordsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...calibrationRecordsOptions(queries, config),
    ...options,
  });
}
