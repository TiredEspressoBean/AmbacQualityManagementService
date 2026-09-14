import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type DuplicateProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_duplicate_create>>;

interface DuplicateProcessVariables {
    id: string;
    nameSuffix?: string;
}

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const processWithStepsKeyOptions = () => ({ queryKey: ["process-with-steps"] as const });
const processesKeyOptions = () => ({ queryKey: ["processes"] as const });

export const useDuplicateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<DuplicateProcessResponse, unknown, DuplicateProcessVariables>({
        mutationFn: ({ id, nameSuffix }) =>
            api.api_Processes_with_steps_duplicate_create(
                { name_suffix: nameSuffix || " (Copy)" },
                {
                    params: { id },
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                }
            ),
        onSuccess: () => {
            queryClient.invalidateQueries(processWithStepsKeyOptions());
            queryClient.invalidateQueries(processesKeyOptions());
        },
    });
};
