import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export const retrieveHeatMapAnnotationOptions = (id: string) => queryOptions({
    queryKey: ["heatMapAnnotation", id] as const,
    queryFn: () => api.api_HeatMapAnnotation_retrieve({ params: { id } }),
});

export function useRetrieveHeatMapAnnotation (id: string) {
    return useQuery({
        ...retrieveHeatMapAnnotationOptions(id),
        enabled: !!id,
    });
};
