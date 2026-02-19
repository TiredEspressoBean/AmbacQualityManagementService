import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useRetrieveTrainingRecord(id: string) {
    return useQuery({
        queryKey: ["training-record", id],
        queryFn: () => api.api_TrainingRecords_retrieve({ params: { id } }),
        enabled: !!id && id !== "new",
    });
}
