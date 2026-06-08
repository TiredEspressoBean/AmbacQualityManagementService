import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

type QualityReportsListQueries = NonNullable<operations["api_QualityReports_list"]["parameters"]["query"]>;
type QualityReportsListResponse = components["schemas"]["PaginatedQualityReportsList"];

type MeasurementDefinitionsListQueries = NonNullable<operations["api_MeasurementDefinitions_list"]["parameters"]["query"]>;
type MeasurementDefinitionsListResponse = components["schemas"]["PaginatedMeasurementDefinitionList"];

type ListHookConfig = {
  headers?: Record<string, string>;
};

export const qualityReportsOptions = (queries?: QualityReportsListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["quality-reports", queries, config] as const,
    queryFn: () =>
      api.api_QualityReports_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<QualityReportsListResponse>,
  });

export const qualityReportsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "QualityReports"] as const,
    queryFn: () => api.api_QualityReports_metadata_retrieve(),
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
    queries?: QualityReportsListQueries,
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
