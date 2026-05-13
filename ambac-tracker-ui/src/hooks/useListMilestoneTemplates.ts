import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type TemplatesListQueries = Parameters<typeof api.api_MilestoneTemplates_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_MilestoneTemplates_list>[0];

export const listMilestoneTemplatesOptions = (queries?: TemplatesListQueries) => queryOptions({
    queryKey: ["milestoneTemplates", queries] as const,
    queryFn: () => api.api_MilestoneTemplates_list(
        (queries ? { queries } : undefined) as never,
    ),
});

export function useListMilestoneTemplates(
    queries?: TemplatesListQueries,
    options?: Omit<ReturnType<typeof listMilestoneTemplatesOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...listMilestoneTemplatesOptions(queries),
        ...options,
    });
}
