import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type DefectTrendDataPoint = {
    date: string;
    label: string;
    count: number;
    ts: number;
};

export type DefectTrendSummary = {
    total: number;
    daily_avg: number;
    trend_direction: "up" | "down" | "flat";
    trend_change: number;
};

export type DefectTrendResponse = {
    data: DefectTrendDataPoint[];
    summary: DefectTrendSummary;
};

/** The drill-down filters the chart honours. Same three the records table
 *  takes, matched the same way server-side, so the chart and the table always
 *  describe the same set of defects. */
export type DefectTrendFilters = {
    defect_type?: string | null;
    process?: string | null;
    part_type?: string | null;
};

type UseDefectTrendParams = DefectTrendFilters & {
    days?: number;
    enabled?: boolean;
};

export const defectTrendOptions = (days: number, filters: DefectTrendFilters = {}) => {
    const { defect_type, process, part_type } = filters;
    return queryOptions({
        // Filters belong in the key: without them every selection read the
        // cached unfiltered series and the chart never moved.
        queryKey: ["defect-trend", days, defect_type ?? null, process ?? null, part_type ?? null] as const,
        queryFn: () => api.api_dashboard_defect_trend_retrieve({
            queries: {
                days,
                // Omitted rather than sent null — the backend treats a missing
                // param as "no filter", and a literal "null" would match nothing.
                ...(defect_type ? { defect_type } : {}),
                ...(process ? { process } : {}),
                ...(part_type ? { part_type } : {}),
            },
        }) as Promise<DefectTrendResponse>,
    });
};

export const useDefectTrend = ({
    days = 30,
    enabled = true,
    defect_type = null,
    process = null,
    part_type = null,
}: UseDefectTrendParams = {}) => {
    return useQuery({
        ...defectTrendOptions(days, { defect_type, process, part_type }),
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - trend data
    });
};
