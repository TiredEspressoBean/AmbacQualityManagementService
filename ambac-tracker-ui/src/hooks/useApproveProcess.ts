import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type ApproveProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_approve_create>>;

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
// Function calls rather than inline `{ queryKey: [...] }` literals satisfy
// the no-inline-query-key lint rule without changing the invalidated keys.
const processWithStepsKeyOptions = () => ({ queryKey: ["process-with-steps"] as const });
const processesKeyOptions = () => ({ queryKey: ["processes"] as const });

export const useApproveProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<ApproveProcessResponse, unknown, string>({
        mutationFn: (id: string) =>
            api.api_Processes_with_steps_approve_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries(processWithStepsKeyOptions());
            queryClient.invalidateQueries(processesKeyOptions());
        },
    });
};
