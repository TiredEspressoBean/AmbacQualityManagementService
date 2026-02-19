import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api, type PaginatedQualityReportsList, type PaginatedMeasurementDefinitionList } from "@/lib/api/generated";

export function useQualityReports(
    queries?: Parameters<typeof api.api_ErrorReports_list>[0],
    options?: Omit<
        UseQueryOptions<
            PaginatedQualityReportsList,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery<PaginatedQualityReportsList, Error>({
        queryKey: ["quality-reports", queries],
        queryFn: () => api.api_ErrorReports_list(queries),
        ...options
    });
}

export function useMeasurementDefinitions(
    queries?: Parameters<typeof api.api_MeasurementDefinitions_list>[0],
    options?: Omit<
        UseQueryOptions<
            PaginatedMeasurementDefinitionList,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery<PaginatedMeasurementDefinitionList, Error>({
        queryKey: ["measurement-definitions", queries],
        queryFn: () => api.api_MeasurementDefinitions_list(queries),
        ...options
    });
}