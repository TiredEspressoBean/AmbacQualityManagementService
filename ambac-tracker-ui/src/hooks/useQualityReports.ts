import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type ErrorReportsListQueries = NonNullable<operations["api_ErrorReports_list"]["parameters"]["query"]>;
type ErrorReportsListResponse = components["schemas"]["PaginatedQualityReportsList"];

type MeasurementDefinitionsListQueries = NonNullable<operations["api_MeasurementDefinitions_list"]["parameters"]["query"]>;
type MeasurementDefinitionsListResponse = components["schemas"]["PaginatedMeasurementDefinitionList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const qualityReportsOptions = (queries?: ErrorReportsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["quality-reports", queries, config] as const,
    queryFn: () =>
      api.api_ErrorReports_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<ErrorReportsListResponse>,
  });

export const qualityReportsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "QualityReports", "ErrorReports"] as const,
    queryFn: () => api.api_ErrorReports_metadata_retrieve(),
  });

export const measurementDefinitionsOptions = (queries?: MeasurementDefinitionsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["measurement-definitions", queries, config] as const,
    queryFn: () =>
      api.api_MeasurementDefinitions_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<MeasurementDefinitionsListResponse>,
  });

export function useQualityReports(
    queries?: ErrorReportsListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof qualityReportsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...qualityReportsOptions(queries, config),
        ...options,
    });
}

export function useMeasurementDefinitions(
    queries?: MeasurementDefinitionsListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof measurementDefinitionsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...measurementDefinitionsOptions(queries, config),
        ...options,
    });
}
