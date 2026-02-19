import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingRequirements_list>[0];

export function useTrainingRequirements(options: ListParams = {}) {
    return useQuery({
        queryKey: ["training-requirements", options],
        queryFn: () => api.api_TrainingRequirements_list(options),
    });
}
