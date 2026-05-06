import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type ErrorReportsListQueries = NonNullable<operations["api_ErrorReports_list"]["parameters"]["query"]>;
type ErrorReportsListResponse = components["schemas"]["PaginatedQualityReportsList"];

type MeasurementDefinitionsListQueries = NonNullable<operations["api_MeasurementDefinitions_list"]["parameters"]["query"]>;
type MeasurementDefinitionsListResponse = components["schemas"]["PaginatedMeasurementDefinitionList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useQualityReports(
    queries?: ErrorReportsListQueries,
    config?: ListHookConfig,
    options?: Omit<UseQueryOptions<ErrorReportsListResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery<ErrorReportsListResponse, Error>({
        queryKey: ["quality-reports", queries, config],
        queryFn: () =>
            api.api_ErrorReports_list(
                (queries || config ? { queries, ...config } : undefined) as never,
            ) as Promise<ErrorReportsListResponse>,
        ...options,
    });
}

export function useMeasurementDefinitions(
    queries?: MeasurementDefinitionsListQueries,
    config?: ListHookConfig,
    options?: Omit<UseQueryOptions<MeasurementDefinitionsListResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery<MeasurementDefinitionsListResponse, Error>({
        queryKey: ["measurement-definitions", queries, config],
        queryFn: () =>
            api.api_MeasurementDefinitions_list(
                (queries || config ? { queries, ...config } : undefined) as never,
            ) as Promise<MeasurementDefinitionsListResponse>,
        ...options,
    });
}
