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

type UseDefectsByProcessParams = {
    days?: number;
    limit?: number;
    enabled?: boolean;
};

const fetchDefectsByProcess = (days: number, limit: number) =>
    api.api_dashboard_defects_by_process_retrieve({ queries: { days, limit } }) as Promise<DefectsByProcessResponse>;

export const defectsByProcessOptions = (days: number, limit: number) => queryOptions({
    queryKey: ["defects-by-process", days, limit] as const,
    queryFn: () => fetchDefectsByProcess(days, limit),
    placeholderData: (previousData) => previousData,
    refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
});

export const useDefectsByProcess = ({ days = 30, limit = 10, enabled = true }: UseDefectsByProcessParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery(defectsByProcessOptions(d, limit));
        });
    }, [days, limit, queryClient]);

    return useQuery({ ...defectsByProcessOptions(days, limit), enabled });
};
