import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useQualityReports(
    queries: Parameters<typeof api.api_ErrorReports_list>[0],
    options?: Omit<
        UseQueryOptions<
            Awaited<ReturnType<typeof api.api_ErrorReports_list>>,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery({
        queryKey: ["quality-reports", queries],
        queryFn: () => api.api_ErrorReports_list(queries),
        ...options
    });
}

export function useMeasurementDefinitions(
    queries: Parameters<typeof api.api_MeasurementDefinitions_list>[0],
    options?: Omit<
        UseQueryOptions<
            Awaited<ReturnType<typeof api.api_MeasurementDefinitions_list>>,
            Error
        >,
        "queryKey" | "queryFn"
    >
) {
    return useQuery({
        queryKey: ["measurement-definitions", queries],
        queryFn: () => api.api_MeasurementDefinitions_list(queries),
        ...options
    });
}