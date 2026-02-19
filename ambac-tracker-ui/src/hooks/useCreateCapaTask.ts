import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateCapaTaskInput = Parameters<typeof api.api_CapaTasks_create>[0];
type CreateCapaTaskResponse = Awaited<ReturnType<typeof api.api_CapaTasks_create>>;

export const useCreateCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaTaskResponse, unknown, CreateCapaTaskInput>({
        mutationFn: (data) =>
            api.api_CapaTasks_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
