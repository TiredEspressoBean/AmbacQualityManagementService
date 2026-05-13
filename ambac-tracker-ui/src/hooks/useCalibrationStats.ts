import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const calibrationStatsOptions = () => queryOptions({
    queryKey: ["calibration-records", "stats"] as const,
    queryFn: () => api.api_CalibrationRecords_stats_retrieve(),
});

export function useCalibrationStats() {
    return useQuery(calibrationStatsOptions());
}
