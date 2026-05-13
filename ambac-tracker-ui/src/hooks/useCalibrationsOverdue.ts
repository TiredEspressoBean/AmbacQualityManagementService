import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const calibrationsOverdueOptions = () => queryOptions({
    queryKey: ["calibration-records", "overdue"] as const,
    queryFn: () => api.api_CalibrationRecords_overdue_list(),
});

export function useCalibrationsOverdue() {
    return useQuery(calibrationsOverdueOptions());
}
