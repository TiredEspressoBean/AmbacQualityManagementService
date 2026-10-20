import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

/** What a release answered, tagged with which exit it was. */
export type CoreReleaseResult =
    | { to: "rebuild"; result: Schema<"CoreReleaseRebuild"> }
    | { to: "inventory"; result: Schema<"CoreReleaseInventory"> };

/**
 * Release a torn-down core to its exit: rebuild (repair and return) or inventory
 * (everything else). Which one is legal follows from the core's fulfilment mode and
 * is enforced server-side — this hook just carries the intent.
 *
 * Invalidates work orders as well as cores: the release changes the core's status,
 * and the teardown WO's control page is where that status is being read.
 */
export function useReleaseCore() {
    const queryClient = useQueryClient();
    return useMutation<CoreReleaseResult, unknown, { id: string; to: "rebuild" | "inventory" }>({
        mutationFn: async ({ id, to }): Promise<CoreReleaseResult> => {
            const opts = { params: { id }, headers: { "X-CSRFToken": getCookie("csrftoken") } };
            return to === "rebuild"
                ? { to, result: await api.api_Cores_release_to_rebuild_create(undefined, opts) }
                : { to, result: await api.api_Cores_release_to_inventory_create(undefined, opts) };
        },
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) =>
                    // lower-cased compare: the work-order hook keys on "workorder",
                    // not "workOrder", and a near-miss here fails silently — the
                    // release succeeds and the row it changed never refreshes.
                    ["core", "cores", "workorder", "workorders", "rebuildplan"].includes(
                        String(q.queryKey[0]).toLowerCase(),
                    ),
            });
        },
    });
}


/**
 * The rest of the core lifecycle: close out a teardown, pause for authorisation,
 * record what the customer said, dispatch the unit back. Same invalidation as
 * `useReleaseCore` — each changes the core's status, and the work-order surface is
 * where that is read.
 *
 * `complete_disassembly` had a service, an endpoint and its own permission, and no
 * caller anywhere in the app. A core could be started into teardown and never taken
 * out of it, which stranded everything downstream: release to rebuild or inventory,
 * authorisation, and the return all require DISASSEMBLED or later.
 */
export function useCoreLifecycleAction() {
    const queryClient = useQueryClient();
    return useMutation<
        unknown,
        unknown,
        | { id: string; action: "complete_disassembly" }
        | { id: string; action: "request_authorisation" }
        | {
            id: string; action: "record_authorisation"; approved: boolean; note?: string;
            /** Who at the customer answered, how, and the reference — no login needed. */
            contact?: string; method?: string; reference?: string;
        }
        | { id: string; action: "approve_repair"; code: string; note?: string }
    >({
        mutationFn: (v) => {
            const headers = { "X-CSRFToken": getCookie("csrftoken") };
            if (v.action === "complete_disassembly") {
                return api.api_Cores_complete_disassembly_create(undefined, {
                    params: { id: v.id }, headers,
                });
            }
            if (v.action === "request_authorisation") {
                return api.api_Cores_request_authorisation_create(undefined, {
                    params: { id: v.id }, headers,
                });
            }
            if (v.action === "record_authorisation") {
                return api.api_Cores_record_authorisation_create(
                    {
                        approved: v.approved, note: v.note ?? "",
                        contact: v.contact ?? "", method: v.method ?? "", reference: v.reference ?? "",
                    },
                    { params: { id: v.id }, headers },
                );
            }
            // A return to the customer is a shipment: see ShipDialog.
            return api.api_Cores_approve_repair_create(
                { code: v.code, note: v.note ?? "" },
                { params: { id: v.id }, headers },
            );
        },
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) =>
                    // "parts": a unit held at a check re-reads its repair options.
                    ["core", "cores", "workorder", "workorders", "rebuildplan", "parts"].includes(
                        String(q.queryKey[0]).toLowerCase(),
                    ),
            });
        },
    });
}
