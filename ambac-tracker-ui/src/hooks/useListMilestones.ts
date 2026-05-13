import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type MilestonesListQueries = Parameters<typeof api.api_Milestones_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Milestones_list>[0];

export const listMilestonesOptions = (queries?: MilestonesListQueries) => queryOptions({
    queryKey: ["milestones", queries] as const,
    queryFn: () => api.api_Milestones_list(
        (queries ? { queries } : undefined) as never,
    ),
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
