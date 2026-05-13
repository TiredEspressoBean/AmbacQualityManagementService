import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateProcessInput = Schema<"PatchedProcessesRequest">;
type UpdateProcessResponse = Schema<"Processes">;

type UpdateProcessVariables = {
    id: string;
    data: UpdateProcessInput;
};

export const useUpdateProcess = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateProcessResponse, unknown, UpdateProcessVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Processes_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateProcessResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["process"],
                predicate: (query) => query.queryKey[0] === "process",
            });
        },
    });
};
