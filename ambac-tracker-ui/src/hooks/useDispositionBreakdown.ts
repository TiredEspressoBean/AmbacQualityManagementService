import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { useEffect } from "react";

export type DispositionTypeData = {
    type: string;
    count: number;
    percentage: number;
};

export type DispositionBreakdownResponse = {
    data: DispositionTypeData[];
    total: number;
};

type UseDispositionBreakdownParams = {
    days?: number;
    enabled?: boolean;
};

const fetchDispositionBreakdown = (days: number) =>
    api.api_dashboard_disposition_breakdown_retrieve({ queries: { days } }) as Promise<DispositionBreakdownResponse>;

export const dispositionBreakdownOptions = (days: number) => queryOptions({
    queryKey: ["disposition-breakdown", days] as const,
    queryFn: () => fetchDispositionBreakdown(days),
    placeholderData: (previousData) => previousData,
    refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
});

export const useDispositionBreakdown = ({ days = 30, enabled = true }: UseDispositionBreakdownParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery(dispositionBreakdownOptions(d));
        });
    }, [days, queryClient]);

    return useQuery({ ...dispositionBreakdownOptions(days), enabled });
};
