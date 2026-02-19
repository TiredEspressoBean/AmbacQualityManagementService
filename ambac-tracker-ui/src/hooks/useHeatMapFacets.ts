import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

interface FacetFilters {
    model?: number;
    part?: number;
    part__work_order?: number;
    created_at__gte?: string;
    created_at__lte?: string;
}

export function useHeatMapFacets(
    filters: FacetFilters,
    options?: { enabled?: boolean }
) {
    return useQuery({
        queryKey: ["heatmap-facets", filters],
        queryFn: () => api.api_HeatMapAnnotation_facets_retrieve(filters),
        enabled: options?.enabled ?? true,
    });
}
