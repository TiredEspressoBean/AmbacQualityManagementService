import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type CalibrationRecordResponse = Schema<"CalibrationRecord">;

export function useRetrieveCalibrationRecord(id: string) {
    return useQuery<CalibrationRecordResponse>({
        queryKey: ["calibration-record", id],
        queryFn: () => api.api_CalibrationRecords_retrieve({ params: { id } }) as Promise<CalibrationRecordResponse>,
        enabled: !!id && id !== "new",
    });
}
