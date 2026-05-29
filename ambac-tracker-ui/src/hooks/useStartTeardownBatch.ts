import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type StartTeardownBatchVars = {
    core_ids: string[];
    process_id?: string;
};

export const useStartTeardownBatch = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: StartTeardownBatchVars) =>
            api.api_Cores_start_teardown_batch_create(
                { core_ids: vars.core_ids, ...(vars.process_id ? { process_id: vars.process_id } : {}) } as never,
                { headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (q) =>
                    q.queryKey[0] === "cores" ||
                    q.queryKey[0] === "core" ||
                    q.queryKey[0] === "workorder" ||
                    q.queryKey[0] === "work-order",
            });
        },
    });
};