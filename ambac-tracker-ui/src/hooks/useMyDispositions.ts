/** Quarantine dispositions assigned to the current user that are still open —
 *  a real, existing workflow (the disposition auto-create signal assigns a QA
 *  user). due_date drives the inbox's urgency horizons. */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";

// Derived, not hand-written: Pick from the generated schema so a regen
// updates nullability/fields here automatically (hand-copied shapes drift).
type Disposition = components["schemas"]["QuarantineDisposition"];
export type MyDisposition = Pick<
    Disposition,
    "id" | "disposition_number" | "current_state" | "disposition_type"
    | "severity" | "severity_display" | "description" | "due_date"
    | "work_order_erp_id"
>;

export function useMyDispositions(userPk: number | null | undefined) {
    return useQuery({
        queryKey: ["my-dispositions", userPk] as const,
        enabled: userPk != null,
        queryFn: async () => {
            const resp = await api.api_QuarantineDispositions_list({
                queries: { assigned_to: userPk, limit: 50 },
            } as never);
            // No cast: the zod-inferred rows structurally satisfy the
            // schema-derived MyDisposition (BlankEnum is patched to
            // z.literal("") by scripts/fix-generated-api.cjs).
            const rows: MyDisposition[] = resp.results ?? [];
            // Open work only — the filterset has no state__in, so exclude
            // CLOSED client-side to keep OPEN and IN_PROGRESS together.
            return rows.filter((d) => d.current_state !== "CLOSED");
        },
        staleTime: 30_000,
    });
}
