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

export const locationContentsOptions = (id: string, days = 7, includeChildren = true) =>
    queryOptions({
        queryKey: ["locations", "contents", id, days, includeChildren],
        queryFn: () => api.api_StorageLocations_contents_retrieve(
            { params: { id }, queries: { days, include_children: includeChildren } }) as Promise<LocationContents>,
    });

function useInvalidate() {
    const qc = useQueryClient();
    return () => {
        void qc.invalidateQueries({ queryKey: ["locations"] });
        void qc.invalidateQueries({ queryKey: ["material-lot"] });
        void qc.invalidateQueries({ queryKey: ["material-lots"] });
    };
}

export function useMoveLot() {
    const invalidate = useInvalidate();
    return useMutation({
        mutationFn: ({ id, to, quantity, reason }: { id: string; to: string; quantity?: string | null; reason?: string }) =>
            // MaterialLots actions go as multipart (the viewset lists MultiPart first, for
            // CoC uploads), where a null travels as the text "null" — so leave it out.
            api.api_MaterialLots_move_create({ to, reason: reason ?? "", ...(quantity ? { quantity } : {}) }, { params: { id } }),
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
