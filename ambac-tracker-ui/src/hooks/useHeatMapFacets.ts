import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

interface FacetFilters {
    model?: number;
    part?: number;
    part__work_order?: number;
    created_at__gte?: string;
    created_at__lte?: string;
}

export const heatMapFacetsOptions = (filters: FacetFilters) => queryOptions({
    queryKey: ["heatmap-facets", filters] as const,
    queryFn: () => api.api_HeatMapAnnotation_facets_retrieve(filters as never),
});

export function useHeatMapFacets(
    filters: FacetFilters,
    options?: { enabled?: boolean }
) {
    return useQuery({
        ...heatMapFacetsOptions(filters),
        enabled: options?.enabled ?? true,
    });
}
