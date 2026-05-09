import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type TrainingRecordResponse = Schema<"TrainingRecord">;

export function useRetrieveTrainingRecord(id: string) {
    return useQuery<TrainingRecordResponse>({
        queryKey: ["training-record", id],
        queryFn: () => api.api_TrainingRecords_retrieve({ params: { id } }) as Promise<TrainingRecordResponse>,
        enabled: !!id && id !== "new",
    });
}
