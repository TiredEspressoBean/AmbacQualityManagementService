import { api } from "@/lib/api/generated";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

export type RepeatDefectData = {
    error_type: string;
    count: number;
    part_types_affected: string[];
    processes_affected: string[];
};

export type RepeatDefectsResponse = {
    data: RepeatDefectData[];
    total_repeat_count: number;
};

type UseRepeatDefectsParams = {
    days?: number;
    minOccurrences?: number;
    limit?: number;
    enabled?: boolean;
};

const fetchRepeatDefects = (days: number, minOccurrences: number, limit: number) =>
    api.api_dashboard_repeat_defects_retrieve({ days, min_occurrences: minOccurrences, limit }) as Promise<RepeatDefectsResponse>;

export const useRepeatDefects = ({
    days = 30,
    minOccurrences = 3,
    limit = 10,
    enabled = true
}: UseRepeatDefectsParams = {}) => {
    const queryClient = useQueryClient();

    useEffect(() => {
        const rangesToPrefetch = [30, 60, 90].filter(d => d !== days);
        rangesToPrefetch.forEach(d => {
            queryClient.prefetchQuery({
                queryKey: ["repeat-defects", d, minOccurrences, limit],
                queryFn: () => fetchRepeatDefects(d, minOccurrences, limit),
            });
        });
    }, []);

    return useQuery<RepeatDefectsResponse>({
        queryKey: ["repeat-defects", days, minOccurrences, limit],
        queryFn: () => fetchRepeatDefects(days, minOccurrences, limit),
        enabled,
        placeholderData: (previousData) => previousData,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aggregated data
    });
};
