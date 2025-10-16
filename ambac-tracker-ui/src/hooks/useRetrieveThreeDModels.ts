import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"

export function useRetrieveThreeDModels (queries: Parameters<typeof api.api_ThreeDModels_list>[0]) {
    return useQuery({
        queryKey: ["threeDModel", queries],
        queryFn: () => api.api_ThreeDModels_list(queries),
    });
};
