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

export const ncrOptions = (id: string) => queryOptions({
    queryKey: ncrKeys.detail(id),
    queryFn: () => api.api_NCRs_retrieve({ params: { id } }),
});

export function useNcr(id: string | undefined) {
    return useQuery({ ...ncrOptions(id ?? ""), enabled: !!id });
}

/** What a change to an NCR touches: the NCR and its lists, every disposition key (a
 *  decision is a disposition's), and the parts and work orders whose status it moves —
 *  raising one holds its parts, deciding scraps or routes them. */
export function invalidateAfterNcrChange(queryClient: QueryClient) {
    return queryClient.invalidateQueries({
        predicate: (q) => {
            const head = String(q.queryKey[0] ?? "").toLowerCase();
            return ["ncr", "disposition", "part", "work-order", "workorder", "work_order"]
                .some((k) => head.includes(k));
        },
    });
}
