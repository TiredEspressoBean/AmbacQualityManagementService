/** Personal calibration nag: gauges the current user recently used whose
 *  calibration is due soon or overdue — pre-empts the point-of-use gate
 *  (an out-of-cal gauge makes measured parts retroactively suspect). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type GaugeNagRow = {
    equipment_id: string;
    equipment_name: string;
    due_date: string;
    days_until_due: number;
    overdue: boolean;
};

export function useGaugeNag() {
    return useQuery({
        queryKey: ["gaugeNag"] as const,
        queryFn: () =>
            api.api_CalibrationRecords_my_gauge_nag_retrieve() as unknown as Promise<GaugeNagRow[]>,
        staleTime: 60_000,
    });
}
