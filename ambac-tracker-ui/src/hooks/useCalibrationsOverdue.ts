import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useCalibrationsOverdue() {
    return useQuery({
        queryKey: ["calibration-records", "overdue"],
        queryFn: () => api.api_CalibrationRecords_overdue_list(),
    });
}
