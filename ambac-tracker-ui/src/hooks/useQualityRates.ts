import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

export type QualityRatesResponse = {
    scrap_rate: number;
    rework_rate: number;
    use_as_is_rate: number;
    total_inspected: number;
    total_failed: number;
};

type UseQualityRatesParams = {
    days?: number;
    enabled?: boolean;
};

const fetchQualityRates = (days: number) =>
    api.api_dashboard_quality_rates_retrieve({ days }) as Promise<QualityRatesResponse>;

export const useQualityRates = ({ days = 30, enabled = true }: UseQualityRatesParams = {}) => {
    const queryClient = useQueryClient();

    // Prefetch other common ranges on mount
    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery({
                queryKey: ["quality-rates", d],
                queryFn: () => fetchQualityRates(d),
            });
        });
    }, []);

    return useQuery<QualityRatesResponse>({
        queryKey: ["quality-rates", days],
        queryFn: () => fetchQualityRates(days),
        enabled,
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - rate data
    });
};
