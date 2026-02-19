import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useMyTraining() {
    return useQuery({
        queryKey: ["training-records", "my-training"],
        queryFn: () => api.api_TrainingRecords_my_training_list(),
    });
}
