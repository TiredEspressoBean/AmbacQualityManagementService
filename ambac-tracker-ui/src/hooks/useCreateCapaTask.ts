import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateCapaTaskInput = Schema<"CapaTasksRequest">;
type CreateCapaTaskResponse = Schema<"CapaTasks">;

export const useCreateCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaTaskResponse, unknown, CreateCapaTaskInput>({
        mutationFn: (data) =>
            api.api_CapaTasks_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCapaTaskResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-tasks"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
