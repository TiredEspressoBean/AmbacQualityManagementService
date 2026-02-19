import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

type ListParams = Parameters<typeof api.api_CalibrationRecords_due_soon_list>[0];

export function useCalibrationsDueSoon(options: ListParams = {}) {
    return useQuery({
        queryKey: ["calibration-records", "due-soon", options],
        queryFn: () => api.api_CalibrationRecords_due_soon_list(options),
    });
}
