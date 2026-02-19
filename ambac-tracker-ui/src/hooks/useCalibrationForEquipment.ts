import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export function useCalibrationForEquipment(equipmentId: string) {
    return useQuery({
        queryKey: ["calibration-records", "for-equipment", equipmentId],
        queryFn: () => api.api_CalibrationRecords_for_equipment_list({ queries: { equipment_id: equipmentId } }),
        enabled: !!equipmentId,
    });
}
