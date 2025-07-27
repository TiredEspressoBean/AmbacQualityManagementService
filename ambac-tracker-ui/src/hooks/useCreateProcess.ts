import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateProcessesInput = Parameters<typeof api.api_Processes_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_Processes_create>>;

export const useCreateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreateProcessesInput>({
        mutationFn: (data) =>
            api.api_Processes_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["process"] });
        },
    });
};
