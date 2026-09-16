import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

// The `extends { queries?: infer Q }` form this used fell through -- the
// param is optional, so the check failed and Q resolved to the whole config
// object rather than the query shape. Indexing it directly is what was
// meant, and it is what makes the call typecheck without a cast.
type MilestonesListQueries = NonNullable<Parameters<typeof api.api_Milestones_list>[0]>["queries"];

export const listMilestonesOptions = (queries?: MilestonesListQueries) => queryOptions({
    queryKey: ["milestones", queries] as const,
    queryFn: () => api.api_Milestones_list({ queries }),
});

export function useListMilestones(
    queries?: MilestonesListQueries,
    options?: Omit<ReturnType<typeof listMilestonesOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...listMilestonesOptions(queries),
        ...options,
    });
}
