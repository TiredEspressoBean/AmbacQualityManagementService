import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveThreeDModel (id: number) {
    return useQuery({
        queryKey: ["threeDModel", id],
        queryFn: () => api.api_ThreeDModels_retrieve({ params: { id } }),
        enabled: !!id,
    });
};
