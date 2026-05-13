import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type TrainingTypeResponse = Schema<"TrainingType">;

export const retrieveTrainingTypeOptions = (id: string) => queryOptions({
    queryKey: ["training-type", id] as const,
    queryFn: () => api.api_TrainingTypes_retrieve({ params: { id } }) as Promise<TrainingTypeResponse>,
});

export function useRetrieveTrainingType(id: string) {
    return useQuery({
        ...retrieveTrainingTypeOptions(id),
        enabled: !!id && id !== "new",
    });
}
