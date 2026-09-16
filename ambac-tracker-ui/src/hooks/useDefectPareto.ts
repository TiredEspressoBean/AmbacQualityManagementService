import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type ParetoDataPoint = {
    errorType: string;
    count: number;
    cumulative: number;
};

export type DefectParetoResponse = {
    data: ParetoDataPoint[];
    total: number;
};

/** Cross-facet filters. No `defect_type`: this breakdown IS the defect-type
 *  axis and is the control that sets it, so filtering it by its own selection
 *  would leave a single bar at 100% with nothing else to click. It does follow
 *  the other two, so narrowing to a part type narrows which defects are
 *  counted. */
export type DefectParetoFilters = {
    process?: string | null;
    part_type?: string | null;
};

type UseDefectParetoParams = DefectParetoFilters & {
    days?: number;
    limit?: number;
    enabled?: boolean;
};

export const defectParetoOptions = (days: number, limit: number, filters: DefectParetoFilters = {}) => {
    const { process, part_type } = filters;
    return queryOptions({
        // Filters in the key, or a selection reads the cached unfiltered series.
        queryKey: ["defect-pareto", days, limit, process ?? null, part_type ?? null] as const,
        queryFn: () => api.api_dashboard_defect_pareto_retrieve({
            queries: {
                days,
                limit,
                // Omitted rather than sent null: a missing param means "no
                // filter" server-side, a literal null would match nothing.
                ...(process ? { process } : {}),
                ...(part_type ? { part_type } : {}),
            },
        }) as Promise<DefectParetoResponse>,
    });
};

export const useDefectPareto = ({
    days = 30, limit = 10, enabled = true, process = null, part_type = null,
}: UseDefectParetoParams = {}) => {
    return useQuery({
        ...defectParetoOptions(days, limit, { process, part_type }),
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};
