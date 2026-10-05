import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type CycleCount = Schema<"CycleCount">;
export type CountEntry = { kind: "LOT" | "PART"; id: string; counted?: string | null; note?: string };

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
        mutationFn: (body: { location: string; blind: boolean }) =>
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

export function useApplyCount() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: (id: string) => api.api_CycleCounts_apply_create(undefined, { params: { id } }) as Promise<CycleCount>,
        onSuccess: invalidate,
    });
}
