import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type PlanTeardownVars = {
    core_ids: string[];
    /** ISO date the teardown should begin — the proposal's start-by. */
    start_by?: string | null;
    process_id?: string;
};

/**
 * Accept a teardown proposal: plan a PENDING teardown work order for these cores,
 * dated to `start_by`, without starting disassembly. Starting now is
 * `useStartTeardownBatch`.
 */
export const usePlanTeardown = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: PlanTeardownVars) =>
            api.api_Cores_plan_teardown_create(
                {
                    core_ids: vars.core_ids,
                    ...(vars.start_by ? { start_by: vars.start_by } : {}),
                    ...(vars.process_id ? { process_id: vars.process_id } : {}),
                },
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            // The requirements view is where the proposal lives: refreshing it is what
            // makes the accepted row disappear rather than being proposed again.
            queryClient.invalidateQueries({
                predicate: (q) =>
                    q.queryKey[0] === "cores" ||
                    q.queryKey[0] === "core" ||
                    q.queryKey[0] === "workorder" ||
                    q.queryKey[0] === "work-order" ||
                    (q.queryKey[0] === "schedule" && q.queryKey[1] === "requirements"),
            });
        },
    });
};
