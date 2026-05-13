import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateDocumentInput = Schema<"PatchedDocumentsRequest">;
type UpdateDocumentResponse = Schema<"Documents">;

type UpdateDocumentVariables = {
    id: string;
    data: UpdateDocumentInput;
};

export const useUpdateDocument = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateDocumentResponse, unknown, UpdateDocumentVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Documents_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateDocumentResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["document"],
                predicate: (query) => query.queryKey[0] === "equipment",
            });
        },
    });
};
