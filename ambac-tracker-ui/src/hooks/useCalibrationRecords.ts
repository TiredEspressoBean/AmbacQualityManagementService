import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_CalibrationRecords_list>[0];

export function useCalibrationRecords(options: ListParams = {}) {
    return useQuery({
        queryKey: ["calibration-records", options],
        queryFn: () => api.api_CalibrationRecords_list(options),
    });
}
