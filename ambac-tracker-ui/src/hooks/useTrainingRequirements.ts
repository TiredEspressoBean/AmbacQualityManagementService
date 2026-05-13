import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingRequirements_list>[0];

export const trainingRequirementsOptions = (options: ListParams = {}) => queryOptions({
    queryKey: ["training-requirements", options] as const,
    queryFn: () => api.api_TrainingRequirements_list(options),
});

export function useTrainingRequirements(options: ListParams = {}) {
    return useQuery({ ...trainingRequirementsOptions(options) });
}
