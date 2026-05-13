import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_CalibrationRecords_due_soon_list>[0];

export const calibrationsDueSoonOptions = (options: ListParams = {}) => queryOptions({
    queryKey: ["calibration-records", "due-soon", options] as const,
    queryFn: () => api.api_CalibrationRecords_due_soon_list(options),
});

export function useCalibrationsDueSoon(options: ListParams = {}) {
    return useQuery(calibrationsDueSoonOptions(options));
}
