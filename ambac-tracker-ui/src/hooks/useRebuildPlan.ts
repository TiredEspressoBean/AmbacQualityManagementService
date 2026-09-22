import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import type { Schema } from "@/lib/api/types";

type RebuildPlanResponse = Schema<"RebuildPlan">;

export const rebuildPlanOptions = (id: string) =>
    queryOptions({
        queryKey: ["rebuildPlan", id] as const,
        queryFn: () =>
            api.api_Cores_rebuild_plan_retrieve({
                params: { id },
            }) as Promise<RebuildPlanResponse>,
    });

export function useRebuildPlan(id: string, options?: { enabled?: boolean }) {
    return useQuery({ ...rebuildPlanOptions(id), enabled: options?.enabled ?? true });
}
