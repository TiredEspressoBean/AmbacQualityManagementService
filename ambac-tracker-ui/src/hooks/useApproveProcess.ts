import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type ApproveProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_approve_create>>;

export const useApproveProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<ApproveProcessResponse, unknown, string>({
        mutationFn: (id: string) =>
            api.api_Processes_with_steps_approve_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["process-with-steps"] });
            queryClient.invalidateQueries({ queryKey: ["processes"] });
        },
    });
};
