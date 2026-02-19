import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingRecords_expiring_soon_list>[0];

export function useExpiringTraining(options: ListParams = {}) {
    return useQuery({
        queryKey: ["training-records", "expiring-soon", options],
        queryFn: () => api.api_TrainingRecords_expiring_soon_list(options),
    });
}
