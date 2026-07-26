/** Work queue — the operator home's UP NEXT / THEN feed.
 *
 *  Server-ranked WO×step rows: WO priority → due → aging, with `is_held` rows
 *  sunk into a 'blocked' bucket. v1 readiness = ready | blocked (upstream-done
 *  is implicit for open executions; cert/cal/downtime/manual-blocker predicates
 *  layer on later — see design doc §9). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

export type WorkQueueRow = components["schemas"]["WorkQueueRow"];

const KEY = ["workQueue"] as const;

export function useWorkQueue(options?: {
    readiness?: "ready" | "blocked";
    /** e.g. "PRODUCTION" — narrows the queue to a surface. */
    kind?: "PRODUCTION" | "INSPECTION" | "RECEIVING" | "OSP";
    /** WorkCenter ids to filter by (typically the user's memberships or one picked station). */
    workCenterIds?: string[];
    limit?: number;
}) {
    const readiness = options?.readiness;
    const kind = options?.kind;
    const wcs = options?.workCenterIds;
    const limit = options?.limit ?? 20;
    return useQuery({
        queryKey: [...KEY, readiness ?? "all", kind ?? "all", (wcs ?? []).slice().sort().join(","), limit] as const,
        queryFn: async () =>
            (await api.api_WorkQueue_list({
                queries: {
                    ...(readiness ? { readiness } : {}),
                    ...(kind ? { kind } : {}),
                    ...(wcs && wcs.length ? { work_center__in: wcs.join(",") } : {}),
                    limit,
                },
            } as never)).results ?? [],
        staleTime: 15_000,
    });
}
