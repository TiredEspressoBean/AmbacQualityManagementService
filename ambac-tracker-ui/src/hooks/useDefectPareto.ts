import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

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

export const useDefectPareto = ({ days = 30, limit = 10, enabled = true }: UseDefectParetoParams = {}) => {
    return useQuery<DefectParetoResponse>({
        queryKey: ["defect-pareto", days, limit],
        queryFn: () => api.api_dashboard_defect_pareto_retrieve({ days, limit }) as Promise<DefectParetoResponse>,
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};
