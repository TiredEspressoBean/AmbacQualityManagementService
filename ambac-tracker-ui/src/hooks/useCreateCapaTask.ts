import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateCapaTaskInput = Schema<"CapaTasksRequest">;
type CreateCapaTaskResponse = Schema<"CapaTasks">;

// Invalidation-only helpers (not real queryOptions — no queryFn needed).
const capaTasksKeyOptions = () => ({ queryKey: ["capa-tasks"] as const });
const capaKeyOptions = () => ({ queryKey: ["capa"] as const });

export const useCreateCapaTask = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaTaskResponse, unknown, CreateCapaTaskInput>({
        mutationFn: (data) =>
            api.api_CapaTasks_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCapaTaskResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(capaTasksKeyOptions());
            queryClient.invalidateQueries(capaKeyOptions());
        },
    });
};
