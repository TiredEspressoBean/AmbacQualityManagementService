import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type ClearHoldVariables = {
    id: string;
    /** What resolved it — required by the server for Quality and Tooling holds. */
    notes?: string;
    /** A supervisor authorising it, when the person clearing may not clear holds. */
    supervisor?: { email: string; password: string };
};

export const useClearHoldWorkOrder = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (vars: ClearHoldVariables) =>
            api.api_WorkOrders_clear_hold_create({
                notes: vars.notes ?? "",
                ...(vars.supervisor
                    ? { supervisor_email: vars.supervisor.email,
                        supervisor_password: vars.supervisor.password }
                    : {}),
            }, {
                params: { id: vars.id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
                // Every caller says why in its own toast ("Couldn't clear the hold");
                // the 403 interceptor's and the global handler's doubled it (walk 2026-11-16).
                suppressErrorToast: true,
            }),
        meta: { suppressGlobalError: true },
        onSuccess: (_data, vars) => {
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "workorder" && q.queryKey[1] === vars.id,
            });
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "work-order",
            });
        },
    });
};
