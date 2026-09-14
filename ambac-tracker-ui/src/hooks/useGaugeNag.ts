/** Personal calibration nag: gauges the current user recently used whose
 *  calibration is due soon or overdue — pre-empts the point-of-use gate
 *  (an out-of-cal gauge makes measured parts retroactively suspect). */
import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// The action already declares its array response, so this is the client's own
// row type rather than a hand-kept copy that could drift from it.
export type GaugeNagRow = Awaited<
    ReturnType<typeof api.api_CalibrationRecords_my_gauge_nag_list>
>[number];

export const gaugeNagOptions = () =>
    queryOptions({
        queryKey: ["gaugeNag"] as const,
        queryFn: () => api.api_CalibrationRecords_my_gauge_nag_list(),
        staleTime: 60_000,
    });

export function useGaugeNag() {
    return useQuery(gaugeNagOptions());
}
