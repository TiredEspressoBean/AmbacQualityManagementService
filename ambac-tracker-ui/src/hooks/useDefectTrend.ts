import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

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

type UseDefectTrendParams = {
    days?: number;
    enabled?: boolean;
};

export const useDefectTrend = ({ days = 30, enabled = true }: UseDefectTrendParams = {}) => {
    return useQuery<DefectTrendResponse>({
        queryKey: ["defect-trend", days],
        queryFn: () => api.api_dashboard_defect_trend_retrieve({ days }) as Promise<DefectTrendResponse>,
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - trend data
    });
};
