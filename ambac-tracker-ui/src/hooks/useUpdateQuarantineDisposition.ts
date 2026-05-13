import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateQuarantineDispositionInput = Schema<"PatchedQuarantineDispositionRequest">;
type UpdateQuarantineDispositionResponse = Schema<"QuarantineDisposition">;

type UpdateQuarantineDispositionVariables = {
    id: string;
    data: UpdateQuarantineDispositionInput;
};

export const useUpdateQuarantineDisposition = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateQuarantineDispositionResponse, unknown, UpdateQuarantineDispositionVariables>({
        mutationFn: ({ id, data }) =>
            api.api_QuarantineDispositions_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateQuarantineDispositionResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["quarantine-dispositions"],
                predicate: (query) => query.queryKey[0] === "quarantine-dispositions",
            });
        },
    });
};
