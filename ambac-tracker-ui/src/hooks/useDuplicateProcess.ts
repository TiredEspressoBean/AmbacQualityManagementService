import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type DuplicateProcessResponse = Awaited<ReturnType<typeof api.api_Processes_with_steps_duplicate_create>>;

interface DuplicateProcessVariables {
    id: string;
    nameSuffix?: string;
}

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
            queryClient.invalidateQueries({ queryKey: ["process-with-steps"] });
            queryClient.invalidateQueries({ queryKey: ["processes"] });
        },
    });
};
