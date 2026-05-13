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

type UseDefectParetoParams = {
    days?: number;
    limit?: number;
    enabled?: boolean;
};

export const defectParetoOptions = (days: number, limit: number) => queryOptions({
    queryKey: ["defect-pareto", days, limit] as const,
    queryFn: () => api.api_dashboard_defect_pareto_retrieve({ queries: { days, limit } }) as Promise<DefectParetoResponse>,
});

export const useDefectPareto = ({ days = 30, limit = 10, enabled = true }: UseDefectParetoParams = {}) => {
    return useQuery({
        ...defectParetoOptions(days, limit),
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};
