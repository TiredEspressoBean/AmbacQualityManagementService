import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type PaginatedQualityReportsList, type PaginatedMeasurementDefinitionList } from "@/lib/api/generated";

// Extract queries types from Zodios endpoints
type ErrorReportsListQueries = Parameters<typeof api.api_ErrorReports_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_ErrorReports_list>[0];
type MeasurementDefinitionsListQueries = Parameters<typeof api.api_MeasurementDefinitions_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_MeasurementDefinitions_list>[0];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export function useQualityReports(
    queries?: ErrorReportsListQueries,
    config?: ListHookConfig,
    options?: Omit<
        UseQueryOptions<
            PaginatedQualityReportsList,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery<PaginatedQualityReportsList, Error>({
        queryKey: ["quality-reports", queries, config],
        queryFn: () => api.api_ErrorReports_list(queries || config ? { queries, ...config } : undefined),
        ...options
    });
}

export function useMeasurementDefinitions(
    queries?: MeasurementDefinitionsListQueries,
    config?: ListHookConfig,
    options?: Omit<
        UseQueryOptions<
            PaginatedMeasurementDefinitionList,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery<PaginatedMeasurementDefinitionList, Error>({
        queryKey: ["measurement-definitions", queries, config],
        queryFn: () => api.api_MeasurementDefinitions_list(queries || config ? { queries, ...config } : undefined),
        ...options
    });
}
