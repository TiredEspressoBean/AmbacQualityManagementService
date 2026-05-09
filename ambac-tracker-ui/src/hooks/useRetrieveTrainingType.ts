import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type TrainingTypeResponse = Schema<"TrainingType">;

export function useRetrieveTrainingType(id: string) {
    return useQuery<TrainingTypeResponse>({
        queryKey: ["training-type", id],
        queryFn: () => api.api_TrainingTypes_retrieve({ params: { id } }) as Promise<TrainingTypeResponse>,
        enabled: !!id && id !== "new",
    });
}
