import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const expiredTrainingOptions = () => queryOptions({
    queryKey: ["training-records", "expired"] as const,
    queryFn: () => api.api_TrainingRecords_expired_list(),
});

export function useExpiredTraining() {
    return useQuery({ ...expiredTrainingOptions() });
}
