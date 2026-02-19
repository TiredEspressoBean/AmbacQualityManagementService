import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useExpiredTraining() {
    return useQuery({
        queryKey: ["training-records", "expired"],
        queryFn: () => api.api_TrainingRecords_expired_list(),
    });
}
