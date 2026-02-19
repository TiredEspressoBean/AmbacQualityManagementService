import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
    api.api_dashboard_defects_by_process_retrieve({ days, limit }) as Promise<DefectsByProcessResponse>;

export const useDefectsByProcess = ({ days = 30, limit = 10, enabled = true }: UseDefectsByProcessParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery({
                queryKey: ["defects-by-process", d, limit],
                queryFn: () => fetchDefectsByProcess(d, limit),
            });
        });
    }, []);

    return useQuery<DefectsByProcessResponse>({
        queryKey: ["defects-by-process", days, limit],
        queryFn: () => fetchDefectsByProcess(days, limit),
        enabled,
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};
