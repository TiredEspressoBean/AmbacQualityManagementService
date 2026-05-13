import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdatePartTypeInput = Schema<"PatchedPartTypesRequest">;
type UpdatePartTypeResponse = Schema<"PartTypes">;

type UpdatePartTypeVariables = {
    id: string;
    data: UpdatePartTypeInput;
};

export const useUpdatePartType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdatePartTypeResponse, unknown, UpdatePartTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_PartTypes_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdatePartTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["parttypes"],
                predicate: (query) => query.queryKey[0] === "parttypes",
            });
        },
    });
};
