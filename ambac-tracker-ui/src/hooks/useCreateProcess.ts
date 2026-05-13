import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateProcessInput = Schema<"ProcessesRequest">;
type CreateProcessResponse = Schema<"Processes">;

export const useCreateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateProcessResponse, unknown, CreateProcessInput>({
        mutationFn: (data) =>
            api.api_Processes_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateProcessResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["process"] });
        },
    });
};
