import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

export type AgingBucket = {
    bucket: string;
    count: number;
};

export type NcrAgingResponse = {
    data: AgingBucket[];
    avg_age_days: number;
    overdue_count: number;
};

type UseNcrAgingParams = {
    enabled?: boolean;
};

const fetchNcrAging = () =>
    api.api_dashboard_ncr_aging_retrieve() as Promise<NcrAgingResponse>;

export const useNcrAging = ({ enabled = true }: UseNcrAgingParams = {}) => {
    return useQuery<NcrAgingResponse>({
        queryKey: ["ncr-aging"],
        queryFn: fetchNcrAging,
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes - aging data
    });
};
