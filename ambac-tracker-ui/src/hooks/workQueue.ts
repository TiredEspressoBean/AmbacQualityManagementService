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

export function useWorkQueue(options?: { readiness?: "ready" | "blocked"; limit?: number }) {
    return useQuery({
        queryKey: [...KEY, options?.readiness ?? "all", options?.limit ?? 20] as const,
        queryFn: async () =>
            (await api.api_WorkQueue_list({
                queries: {
                    ...(options?.readiness ? { readiness: options.readiness } : {}),
                    limit: options?.limit ?? 20,
                },
            } as never)).results ?? [],
        staleTime: 15_000,
    });
}
