import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type DeprecateProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_deprecate_create>>;

export const useDeprecateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<DeprecateProcessResponse, unknown, string>({
        mutationFn: (id: string) =>
            api.api_Processes_with_steps_deprecate_create(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["process-with-steps"] });
            queryClient.invalidateQueries({ queryKey: ["processes"] });
        },
    });
};
