import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";

export type LocationSummary = Schema<"LocationSummary">;
export type LocationContents = Schema<"LocationContents">;

export const locationSummaryOptions = () =>
    queryOptions({
        queryKey: ["locations", "summary"],
        queryFn: () => api.api_StorageLocations_summary_list() as Promise<LocationSummary[]>,
    });

export const locationContentsOptions = (name: string, days = 7) =>
    queryOptions({
        queryKey: ["locations", "contents", name, days],
        queryFn: () => api.api_StorageLocations_contents_retrieve({ queries: { name, days } }) as Promise<LocationContents>,
    });

function useInvalidate() {
    const qc = useQueryClient();
    return () => {
        void qc.invalidateQueries({ queryKey: ["locations"] });
        void qc.invalidateQueries({ queryKey: ["storage-locations"] });
        void qc.invalidateQueries({ queryKey: ["material-lot"] });
        void qc.invalidateQueries({ queryKey: ["material-lots"] });
    };
}

export function useMoveLot() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ id, to, quantity, reason }: { id: string; to: string; quantity?: string | null; reason?: string }) =>
            api.api_MaterialLots_move_create({ to, quantity: quantity || null, reason: reason ?? "" }, { params: { id } }),
        onSuccess: invalidate,
    });
}

export function useMoveParts() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ part_ids, to, reason }: { part_ids: string[]; to: string; reason?: string }) =>
            api.api_Parts_move_create({ part_ids, to, reason: reason ?? "" }),
        onSuccess: invalidate,
    });
}
