import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

export type FpyDataPoint = {
    date: string;
    label: string;
    fpy: number | null;
    total: number;
    passed: number;
    ts: number;
};

export type FpyTrendResponse = {
    data: FpyDataPoint[];
    average: number;
    total_inspections: number;
    total_passed: number;
};

type UseFpyTrendParams = {
    days?: number;
    enabled?: boolean;
};

const fetchFpyTrend = (days: number) =>
    api.api_dashboard_fpy_trend_retrieve({ days }) as Promise<FpyTrendResponse>;

export const useFpyTrend = ({ days = 30, enabled = true }: UseFpyTrendParams = {}) => {
    const queryClient = useQueryClient();

    // Prefetch other common ranges on mount for instant switching
    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery({
                queryKey: ["fpy-trend", d],
                queryFn: () => fetchFpyTrend(d),
            });
        });
    }, []); // Only on mount

    return useQuery<FpyTrendResponse>({
        queryKey: ["fpy-trend", days],
        queryFn: () => fetchFpyTrend(days),
        enabled,
        placeholderData: (previousData) => previousData, // Keep showing old data while fetching
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - trend data
    });
};
