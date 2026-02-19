import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useRetrieveCalibrationRecord(id: string) {
    return useQuery({
        queryKey: ["calibration-record", id],
        queryFn: () => api.api_CalibrationRecords_retrieve({ params: { id } }),
        enabled: !!id && id !== "new",
    });
}
