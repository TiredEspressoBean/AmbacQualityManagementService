import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

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

const fetchFilterOptions = (days: number) =>
    api.api_dashboard_filter_options_retrieve({ days }) as Promise<FilterOptionsResponse>;

export const useFilterOptions = ({ days = 30, enabled = true }: UseFilterOptionsParams = {}) => {
    return useQuery<FilterOptionsResponse>({
        queryKey: ["filter-options", days],
        queryFn: () => fetchFilterOptions(days),
        enabled,
    });
};
