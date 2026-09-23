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
