import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useRetrieveTrainingType(id: string) {
    return useQuery({
        queryKey: ["training-type", id],
        queryFn: () => api.api_TrainingTypes_retrieve({ params: { id } }),
        enabled: !!id && id !== "new",
    });
}
