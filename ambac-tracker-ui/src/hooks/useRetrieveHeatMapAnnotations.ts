import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveHeatMapAnnotations (queries: Parameters<typeof api.api_HeatMapAnnotation_list>[0]) {
    return useQuery({
        queryKey: ["heatMapAnnotation", queries],
        queryFn: () => api.api_HeatMapAnnotation_list(queries),
    });
};
