import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useTrainingStats() {
    return useQuery({
        queryKey: ["training-records", "stats"],
        queryFn: () => api.api_TrainingRecords_stats_retrieve(),
    });
}
