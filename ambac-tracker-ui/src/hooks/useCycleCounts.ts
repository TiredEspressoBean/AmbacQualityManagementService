import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type CycleCount = Schema<"CycleCount">;
/** One entry while counting. `found_at` (a location) is needed for something found in an
 *  item count, which spans locations. */
export type CountEntry = { kind: "LOT" | "PART"; id: string; counted?: string | null; note?: string; found_at?: string };
export type MissingUnit = Schema<"MissingUnit">;

/** Why the record was off — the lead's reason on each difference (services cycle_count.REASONS). */
export const COUNT_REASONS: { value: string; label: string }[] = [
    { value: "NOT_BOOKED", label: "Used or moved without being booked" },
    { value: "SCRAPPED", label: "Damaged or scrapped, not booked" },
    { value: "MISPLACED", label: "Kept in the wrong place" },
    { value: "RECEIVED_WRONG", label: "Received wrong" },
    { value: "COUNT_ERROR", label: "An earlier count was wrong" },
    { value: "UNKNOWN", label: "Not known" },
];
export const REASON_LABEL: Record<string, string> = Object.fromEntries(COUNT_REASONS.map((r) => [r.value, r.label]));

export const cycleCountsOptions = (location?: string) =>
    queryOptions({
        queryKey: ["cycle-counts", "list", location ?? ""],
        queryFn: () => api.api_CycleCounts_list({ queries: { limit: 100, ...(location ? { location } : {}) } }),
    });

export const cycleCountOptions = (id: string) =>
    queryOptions({
        queryKey: ["cycle-counts", "detail", id],
        queryFn: () => api.api_CycleCounts_retrieve({ params: { id } }) as Promise<CycleCount>,
    });

function useInvalidate() {
    const qc = useQueryClient();
    return () => {
        void qc.invalidateQueries({ queryKey: ["cycle-counts"] });
        void qc.invalidateQueries({ queryKey: ["locations"] });
        void qc.invalidateQueries({ queryKey: ["material-lots"] });
    };
}

export function useStartCount() {
    const invalidate = useInvalidate();
    return useMutation({
        // One scope: a location, or a material or part type wherever it's kept.
        mutationFn: (body: { location?: string; material?: string; part_type?: string; blind: boolean }) =>
            api.api_CycleCounts_create(body) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}

export function useRecordCount() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ id, entries }: { id: string; entries: CountEntry[] }) =>
            api.api_CycleCounts_record_create({ entries }, { params: { id } }) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}

export function useSubmitCount() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: (id: string) => api.api_CycleCounts_submit_create(undefined, { params: { id } }) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}

/** A lead sends a submitted count back for a recount, with a reason. */
export function useSendBackCount() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ id, reason }: { id: string; reason: string }) =>
            api.api_CycleCounts_send_back_create({ reason }, { params: { id } }) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}

/** A lead applies a submitted count. Lines outside their class's tolerance need a note
 *  saying why the difference is real (the server refuses without one). */
export function useApplyCount() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ id, note, reasons }: { id: string; note?: string; reasons: Record<string, string> }) =>
            api.api_CycleCounts_apply_create({ note: note ?? "", reasons } as never, { params: { id } }) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}

export type DueForCount = Schema<"DueForCount">;
export type CountAccuracy = Schema<"CountAccuracy">;

/** Items due for counting under their ABC class, with the locations that cover them. */
export const dueForCountOptions = () =>
    queryOptions({
        queryKey: ["cycle-counts", "due"],
        queryFn: () => api.api_CycleCounts_due_list() as Promise<DueForCount[]>,
    });

export type ItemCountStatus = Schema<"ItemCountStatus">;

/** When one material or part type was last counted and is next due — for its form. */
export const itemCountStatusOptions = (item: { material: string } | { part_type: string }) =>
    queryOptions({
        queryKey: ["cycle-counts", "item-status", item],
        queryFn: () => api.api_CycleCounts_item_status_retrieve({ queries: item }) as Promise<ItemCountStatus>,
    });

/** Inventory record accuracy per ABC class over the last `days`. */
export const countAccuracyOptions = (days = 90) =>
    queryOptions({
        queryKey: ["cycle-counts", "accuracy", days],
        queryFn: () => api.api_CycleCounts_accuracy_retrieve({ queries: { days } }) as Promise<CountAccuracy>,
    });


/** Units a count didn't find, still unresolved. */
export const missingUnitsOptions = () =>
    queryOptions({
        queryKey: ["cycle-counts", "missing"],
        queryFn: () => api.api_CycleCounts_missing_list() as Promise<MissingUnit[]>,
    });

/** Applied counts whose differences haven't been keyed into the ERP yet. */
export const toKeyOptions = () =>
    queryOptions({
        queryKey: ["cycle-counts", "to-key"],
        queryFn: () => api.api_CycleCounts_to_key_list() as Promise<CycleCount[]>,
    });

/** Say what became of a unit a count didn't find. */
export function useResolveMissing() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ countId, part, note }: { countId: string; part: string; note: string }) =>
            api.api_CycleCounts_resolve_missing_create({ part, note }, { params: { id: countId } }),
        onSuccess: invalidate,
    });
}

/** Mark counts' differences as keyed into the ERP. */
export function useMarkKeyed() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: (counts: string[]) => api.api_CycleCounts_mark_keyed_create({ counts }),
        onSuccess: invalidate,
    });
}
