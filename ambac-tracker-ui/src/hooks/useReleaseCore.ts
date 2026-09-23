import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";

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
    return useMutation<unknown, unknown, { id: string; to: "rebuild" | "inventory" }>({
        mutationFn: ({ id, to }) =>
            to === "rebuild"
                ? api.api_Cores_release_to_rebuild_create(undefined, {
                      params: { id },
                      headers: { "X-CSRFToken": getCookie("csrftoken") },
                  })
                : api.api_Cores_release_to_inventory_create(undefined, {
                      params: { id },
                      headers: { "X-CSRFToken": getCookie("csrftoken") },
                  }),
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
 * The rest of the repair-and-return lifecycle: pause for authorisation, record what
 * the customer said, dispatch the unit back. Same invalidation as `useReleaseCore` —
 * each changes the core's status, and the work-order surface is where that is read.
 */
export function useCoreLifecycleAction() {
    const queryClient = useQueryClient();
    return useMutation<
        unknown,
        unknown,
        | { id: string; action: "request_authorisation" }
        | { id: string; action: "record_authorisation"; approved: boolean; note?: string }
        | { id: string; action: "return"; reference?: string }
    >({
        mutationFn: (v) => {
            const headers = { "X-CSRFToken": getCookie("csrftoken") };
            if (v.action === "request_authorisation") {
                return api.api_Cores_request_authorisation_create(undefined, {
                    params: { id: v.id }, headers,
                });
            }
            if (v.action === "record_authorisation") {
                return api.api_Cores_record_authorisation_create(
                    { approved: v.approved, note: v.note ?? "" },
                    { params: { id: v.id }, headers },
                );
            }
            return api.api_Cores_return_to_customer_create(
                { reference: v.reference ?? "" },
                { params: { id: v.id }, headers },
            );
        },
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) =>
                    ["core", "cores", "workorder", "workorders", "rebuildplan"].includes(
                        String(q.queryKey[0]).toLowerCase(),
                    ),
            });
        },
    });
}
