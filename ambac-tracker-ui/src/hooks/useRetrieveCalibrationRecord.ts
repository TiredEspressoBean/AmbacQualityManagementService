import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"
import type { Schema } from "@/lib/api/types";

type CalibrationRecordResponse = Schema<"CalibrationRecord">;

export const retrieveCalibrationRecordOptions = (id: string) => queryOptions({
    queryKey: ["calibration-record", id] as const,
    queryFn: () => api.api_CalibrationRecords_retrieve({ params: { id } }) as Promise<CalibrationRecordResponse>,
});

export function useRetrieveCalibrationRecord(id: string) {
    return useQuery({
        ...retrieveCalibrationRecordOptions(id),
        enabled: !!id && id !== "new",
    });
}
