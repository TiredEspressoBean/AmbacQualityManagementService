import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

export type NcrDataPoint = {
    date: string;
    label: string;
    created: number;
    closed: number;
    net_open: number;
};

export type NcrTrendSummary = {
    total_created: number;
    total_closed: number;
    net_change: number;
};

export type NcrTrendResponse = {
    data: NcrDataPoint[];
    summary: NcrTrendSummary;
};

type UseNcrTrendParams = {
    days?: number;
    enabled?: boolean;
};

const fetchNcrTrend = (days: number) =>
    api.api_dashboard_ncr_trend_retrieve({ days }) as Promise<NcrTrendResponse>;

export const useNcrTrend = ({ days = 30, enabled = true }: UseNcrTrendParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery({
                queryKey: ["ncr-trend", d],
                queryFn: () => fetchNcrTrend(d),
            });
        });
    }, []);

    return useQuery<NcrTrendResponse>({
        queryKey: ["ncr-trend", days],
        queryFn: () => fetchNcrTrend(days),
        enabled,
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - trend data
    });
};
