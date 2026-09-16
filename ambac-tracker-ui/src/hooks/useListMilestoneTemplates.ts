import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// The `extends { queries?: infer Q }` form this used fell through -- the
// param is optional, so the check failed and Q resolved to the whole config
// object rather than the query shape. Indexing it directly is what was
// meant, and it is what makes the call typecheck without a cast.
type TemplatesListQueries = NonNullable<Parameters<typeof api.api_MilestoneTemplates_list>[0]>["queries"];

export const listMilestoneTemplatesOptions = (queries?: TemplatesListQueries) => queryOptions({
    queryKey: ["milestoneTemplates", queries] as const,
    queryFn: () => api.api_MilestoneTemplates_list({ queries }),
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
