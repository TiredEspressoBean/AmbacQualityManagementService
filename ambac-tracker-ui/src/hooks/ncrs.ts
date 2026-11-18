import { queryOptions, useQuery, type QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";

// NCRs — the nonconformance, apart from the decision on each part under it
// (Tracker/services/qms/ncr.py). Mutations live where they're used; each calls
// invalidateAfterNcrChange, since a change reaches its dispositions and parts too.

type NcrListQueries = NonNullable<operations["api_NCRs_list"]["parameters"]["query"]>;
type NcrListResponse = components["schemas"]["PaginatedNCRList"];

export const ncrKeys = {
    all: ["ncrs"] as const,
    list: (queries?: NcrListQueries) => ["ncrs", "list", queries] as const,
    detail: (id: string) => ["ncrs", "detail", id] as const,
};

export const listNcrsOptions = (queries?: NcrListQueries) => queryOptions({
    queryKey: ncrKeys.list(queries),
    queryFn: () => api.api_NCRs_list(queries ? { queries } : undefined) as Promise<NcrListResponse>,
});

export function useListNcrs(queries?: NcrListQueries) {
    return useQuery(listNcrsOptions(queries));
}

/** Part id → the number of the open NCR it's on (its decision there still open), for
 *  pickers to say so before the server refuses ("X is on NCR-…: combine instead"). */
export function useOpenNcrByPart(enabled = true) {
    const { data } = useQuery({ ...listNcrsOptions({ state: "OPEN", limit: 500 }), enabled });
    const byPart = new Map<string, string>();
    for (const n of data?.results ?? []) {
        for (const m of n.members) {
            if (m.part_id && m.disposition_id && m.current_state !== "CLOSED") byPart.set(String(m.part_id), n.ncr_number);
        }
    }
    return byPart;
}

export const ncrOptions = (id: string) => queryOptions({
    queryKey: ncrKeys.detail(id),
    queryFn: () => api.api_NCRs_retrieve({ params: { id } }),
});

export function useNcr(id: string | undefined) {
    // The page shows its own "couldn't load" state; a toast on top says it twice.
    return useQuery({ ...ncrOptions(id ?? ""), enabled: !!id, meta: { suppressGlobalError: true } });
}

/** What a change to an NCR touches: the NCR and its lists, every disposition key (a
 *  decision is a disposition's), the parts and work orders whose status it moves —
 *  raising one holds its parts, deciding scraps or routes them — the inspection records
 *  on it, and the home / dashboard counts that tally all of these. */
const NCR_TOUCHES = ["ncr", "disposition", "part", "work-order", "workorder", "work_order",
    "quality-report", "failed-inspection", "dashboard", "home"];
export function invalidateAfterNcrChange(queryClient: QueryClient) {
    return queryClient.invalidateQueries({
        predicate: (q) => {
            const head = String(q.queryKey[0] ?? "").toLowerCase();
            return NCR_TOUCHES.some((k) => head.includes(k));
        },
    });
}

/** A part's line in an NCR part picker: its type, status and work order — a shipped or
 *  completed part is recorded, not held — and the open NCR it's already on. */
export function partPickerDescription(
    p: { part_type_name?: string | null; part_status?: string | null; work_order_erp_id?: string | null },
    onNcr?: string,
) {
    return [
        p.part_type_name,
        p.part_status ? p.part_status.charAt(0) + p.part_status.slice(1).toLowerCase().replace(/_/g, " ") : null,
        p.work_order_erp_id,
        onNcr ? `on ${onNcr}` : null,
    ].filter(Boolean).join(" · ") || undefined;
}

/** Open NCRs the user owns — "My NCRs" on Home and the NCR list's Mine view. */
export const myNcrsOptions = (userPk: number | null | undefined) => queryOptions({
    queryKey: ["ncrs", "mine", userPk] as const,
    enabled: userPk != null,
    queryFn: () => api.api_NCRs_list({ queries: { assigned_to: userPk!, state: "OPEN", ordering: "created_at", limit: 50 } }),
    select: (d) => d.results ?? [],
});

/** NCRs still waiting for their CAPA call (a combined NCR's is the kept one's): Home's count. */
export const awaitingCapaCallOptions = () => queryOptions({
    queryKey: ["ncrs", "awaiting-capa-count"] as const,
    queryFn: () => api.api_NCRs_list({ queries: { capa_decision__isnull: true, combined_into__isnull: true, limit: 1 } }),
    select: (d) => d.count ?? 0,
});
