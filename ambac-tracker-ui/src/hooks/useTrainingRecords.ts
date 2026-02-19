import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingRecords_list>[0];

export function useTrainingRecords(options: ListParams = {}) {
    return useQuery({
        queryKey: ["training-records", options],
        queryFn: () => api.api_TrainingRecords_list(options),
    });
}
