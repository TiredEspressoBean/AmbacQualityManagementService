import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type FilterOption = {
    value: string;
    label: string;
    count: number;
};

export type FilterOptionsResponse = {
    defect_types: FilterOption[];
    processes: FilterOption[];
    part_types: FilterOption[];
};

type UseFilterOptionsParams = {
    days?: number;
    enabled?: boolean;
};

export const filterOptionsQueryOptions = (days: number) => queryOptions({
    queryKey: ["filter-options", days] as const,
    queryFn: () => api.api_dashboard_filter_options_retrieve({ queries: { days } }) as Promise<FilterOptionsResponse>,
});

export const useFilterOptions = ({ days = 30, enabled = true }: UseFilterOptionsParams = {}) => {
    return useQuery({
        ...filterOptionsQueryOptions(days),
        enabled,
    });
};
