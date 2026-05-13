import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const myTrainingOptions = () => queryOptions({
    queryKey: ["training-records", "my-training"] as const,
    queryFn: () => api.api_TrainingRecords_my_training_list(),
});

export function useMyTraining() {
    return useQuery(myTrainingOptions());
}
