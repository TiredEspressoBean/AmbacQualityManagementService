import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const trainingStatsOptions = () => queryOptions({
    queryKey: ["training-records", "stats"] as const,
    queryFn: () => api.api_TrainingRecords_stats_retrieve(),
});

export function useTrainingStats() {
    return useQuery(trainingStatsOptions());
}
