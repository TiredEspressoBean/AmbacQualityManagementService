import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

type MilestonesListQueries = Parameters<typeof api.api_Milestones_list>[0] extends { queries?: infer Q } ? Q : Parameters<typeof api.api_Milestones_list>[0];

export function useListMilestones(
    queries?: MilestonesListQueries,
    options?: Omit<
        UseQueryOptions<Awaited<ReturnType<typeof api.api_Milestones_list>>, Error>,
        "queryKey" | "queryFn"
    >
) {
    return useQuery({
        queryKey: ["milestones", queries],
        queryFn: () => api.api_Milestones_list(queries ? { queries } : undefined),
        ...options,
    });
}
