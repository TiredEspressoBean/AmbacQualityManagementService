import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingRecords_expiring_soon_list>[0];

export const expiringTrainingOptions = (options: ListParams = {}) => queryOptions({
    queryKey: ["training-records", "expiring-soon", options] as const,
    queryFn: () => api.api_TrainingRecords_expiring_soon_list(options),
});

export function useExpiringTraining(options: ListParams = {}) {
    return useQuery(expiringTrainingOptions(options));
}
