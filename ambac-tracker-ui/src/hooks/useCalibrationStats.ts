import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useCalibrationStats() {
    return useQuery({
        queryKey: ["calibration-records", "stats"],
        queryFn: () => api.api_CalibrationRecords_stats_retrieve(),
    });
}
