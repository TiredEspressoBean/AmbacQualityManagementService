import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { components, operations } from "@/lib/api/generated-types";

// Strict types pulled from the OpenAPI spec (no zod passthrough leakage).
type EquipmentListQueries = NonNullable<operations["api_Equipment_list"]["parameters"]["query"]>;
type EquipmentListResponse = components["schemas"]["PaginatedEquipmentsList"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
  headers?: Record<string, string>;
};

export const equipmentsOptions = (queries?: EquipmentListQueries, config?: ListHookConfig) =>
  queryOptions({
    queryKey: ["equipment", queries, config] as const,
    queryFn: () =>
      api.api_Equipment_list(
        (queries || config ? { queries, ...config } : undefined) as never,
      ) as Promise<EquipmentListResponse>,
  });

export const equipmentsMetadataOptions = () =>
  queryOptions({
    queryKey: ["metadata", "Equipments", "Equipment"] as const,
    queryFn: () => api.api_Equipment_metadata_retrieve(),
  });

export function useRetrieveEquipments(
  queries?: EquipmentListQueries,
  config?: ListHookConfig,
  options?: Omit<ReturnType<typeof equipmentsOptions>, "queryKey" | "queryFn">
) {
  return useQuery({
    ...equipmentsOptions(queries, config),
    ...options,
  });
}
