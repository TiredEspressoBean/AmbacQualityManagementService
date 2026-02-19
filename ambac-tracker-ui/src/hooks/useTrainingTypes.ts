import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_TrainingTypes_list>[0];

export function useTrainingTypes(options: ListParams = {}) {
    return useQuery({
        queryKey: ["training-types", options],
        queryFn: () => api.api_TrainingTypes_list(options),
    });
}
