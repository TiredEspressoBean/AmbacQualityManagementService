import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { useEffect } from "react";

export type ProcessDefectData = {
    process_name: string;
    count: number;
};

export type DefectsByProcessResponse = {
    data: ProcessDefectData[];
    total: number;
};

type UseDefectsByProcessParams = DefectsByProcessFilters & {
    days?: number;
    limit?: number;
    enabled?: boolean;
};

/** Cross-facet filters, mirroring the Pareto: no `process`, because this
 *  breakdown is the process axis and is the control that sets it. */
export type DefectsByProcessFilters = {
    defect_type?: string | null;
    part_type?: string | null;
};

const fetchDefectsByProcess = (days: number, limit: number, filters: DefectsByProcessFilters = {}) => {
    const { defect_type, part_type } = filters;
    return api.api_dashboard_defects_by_process_retrieve({
        queries: {
            days,
            limit,
            ...(defect_type ? { defect_type } : {}),
            ...(part_type ? { part_type } : {}),
        },
    }) as Promise<DefectsByProcessResponse>;
};

export const defectsByProcessOptions = (days: number, limit: number, filters: DefectsByProcessFilters = {}) => {
    const { defect_type, part_type } = filters;
    return queryOptions({
        queryKey: ["defects-by-process", days, limit, defect_type ?? null, part_type ?? null] as const,
        queryFn: () => fetchDefectsByProcess(days, limit, { defect_type, part_type }),
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};

export const useDefectsByProcess = ({
    days = 30, limit = 10, enabled = true, defect_type = null, part_type = null,
}: UseDefectsByProcessParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        // Prefetch other ranges for the CURRENT filter set only — prefetching
        // every range x every filter combination would be a lot of wasted calls.
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery(defectsByProcessOptions(d, limit, { defect_type, part_type }));
        });
    }, [days, limit, queryClient, defect_type, part_type]);

    return useQuery({
        ...defectsByProcessOptions(days, limit, { defect_type, part_type }),
        enabled,
    });
};
