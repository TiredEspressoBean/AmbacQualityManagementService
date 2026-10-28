import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type SubmitProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_submit_for_approval_create>>;

// Invalidation-only helpers, as in useApproveProcess.
const processWithStepsKeyOptions = () => ({ queryKey: ["process-with-steps"] as const });
const processesKeyOptions = () => ({ queryKey: ["processes"] as const });

/** Regulated change control: a routing goes to its approvers instead of being approved
 *  from the editor. It sits in Pending approval until they sign. */
export const useSubmitProcessForApproval = () => {
    const queryClient = useQueryClient();

    return useMutation<SubmitProcessResponse, unknown, string>({
        mutationFn: (id: string) =>
            api.api_Processes_with_steps_submit_for_approval_create({}, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries(processWithStepsKeyOptions());
            queryClient.invalidateQueries(processesKeyOptions());
        },
    });
};
