import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type TrainingRecordResponse = Schema<"TrainingRecord">;

export const retrieveTrainingRecordOptions = (id: string) => queryOptions({
    queryKey: ["training-record", id] as const,
    queryFn: () => api.api_TrainingRecords_retrieve({ params: { id } }) as Promise<TrainingRecordResponse>,
});

export function useRetrieveTrainingRecord(id: string) {
    return useQuery({
        ...retrieveTrainingRecordOptions(id),
        enabled: !!id && id !== "new",
    });
}
