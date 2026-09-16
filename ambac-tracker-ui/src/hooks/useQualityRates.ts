import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { useEffect } from "react";

export type QualityRatesResponse = {
    scrap_rate: number;
    rework_rate: number;
    use_as_is_rate: number;
    total_inspected: number;
    total_failed: number;
};

type UseQualityRatesParams = QualityRatesFilters & {
    days?: number;
    enabled?: boolean;
};

/** The KPI cards follow the same drill-down as everything under them.
 *
 *  `defect_type` narrows the FAILED count only, never the inspected total --
 *  an inspection carries no defect type, so narrowing the denominator would
 *  leave only inspections that already had that defect and every rate would
 *  read 100%. The server enforces that; it is stated here because the
 *  asymmetry is surprising from the call site. */
export type QualityRatesFilters = {
    defect_type?: string | null;
    process?: string | null;
    part_type?: string | null;
};

const fetchQualityRates = (days: number, filters: QualityRatesFilters = {}) => {
    const { defect_type, process, part_type } = filters;
    return api.api_dashboard_quality_rates_retrieve({
        queries: {
            days,
            ...(defect_type ? { defect_type } : {}),
            ...(process ? { process } : {}),
            ...(part_type ? { part_type } : {}),
        },
    }) as Promise<QualityRatesResponse>;
};

export const qualityRatesOptions = (days: number, filters: QualityRatesFilters = {}) => {
    const { defect_type, process, part_type } = filters;
    return queryOptions({
        queryKey: ["quality-rates", days, defect_type ?? null, process ?? null, part_type ?? null] as const,
        queryFn: () => fetchQualityRates(days, { defect_type, process, part_type }),
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - rate data
    });
};

export const useQualityRates = ({
    days = 30, enabled = true, defect_type = null, process = null, part_type = null,
}: UseQualityRatesParams = {}) => {
    const queryClient = useQueryClient();

    // Prefetch other ranges for the current filter set only.
    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery(qualityRatesOptions(d, { defect_type, process, part_type }));
        });
    }, [days, queryClient, defect_type, process, part_type]);

    return useQuery({
        ...qualityRatesOptions(days, { defect_type, process, part_type }),
        enabled,
    });
};
