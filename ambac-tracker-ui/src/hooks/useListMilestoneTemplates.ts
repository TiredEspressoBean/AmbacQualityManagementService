import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type TemplatesListQueries = Parameters<typeof api.api_MilestoneTemplates_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_MilestoneTemplates_list>[0];

export function useListMilestoneTemplates(
    queries?: TemplatesListQueries,
    options?: Omit<
        UseQueryOptions<Awaited<ReturnType<typeof api.api_MilestoneTemplates_list>>, Error>,
        "queryKey" | "queryFn"
    >
) {
    return useQuery({
        queryKey: ["milestoneTemplates", queries],
        queryFn: () => api.api_MilestoneTemplates_list(queries ? { queries } : undefined),
        ...options,
    });
}
