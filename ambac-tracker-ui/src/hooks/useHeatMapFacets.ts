import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

// From the contract rather than hand-written -- and note the call below: these
// have to go under `queries`. Passed flat (as they were, behind a cast) zodios
// sees unknown top-level keys and sends no query string at all, so the facets
// came back unfiltered no matter what the viewer selected.
type FacetFilters = NonNullable<
    Parameters<typeof api.api_HeatMapAnnotation_facets_retrieve>[0]
>["queries"];

export const heatMapFacetsOptions = (filters: FacetFilters) => queryOptions({
    queryKey: ["heatmap-facets", filters] as const,
    queryFn: () => api.api_HeatMapAnnotation_facets_retrieve({ queries: filters }),
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
