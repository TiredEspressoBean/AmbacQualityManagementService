import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveHeatMapAnnotation (id: number) {
    return useQuery({
        queryKey: ["heatMapAnnotation", id],
        queryFn: () => api.api_HeatMapAnnotation_retrieve({ params: { id } }),
        enabled: !!id,
    });
};
