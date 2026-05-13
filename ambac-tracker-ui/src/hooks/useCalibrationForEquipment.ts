import { useQuery, queryOptions } from "@tanstack/react-query"
import { api } from "@/lib/api/generated"

export const calibrationForEquipmentOptions = (equipmentId: string) => queryOptions({
    queryKey: ["calibration-records", "for-equipment", equipmentId] as const,
    queryFn: () => api.api_CalibrationRecords_for_equipment_list({ queries: { equipment_id: equipmentId } }),
});

export function useCalibrationForEquipment(equipmentId: string) {
    return useQuery({
        ...calibrationForEquipmentOptions(equipmentId),
        enabled: !!equipmentId,
    });
}
