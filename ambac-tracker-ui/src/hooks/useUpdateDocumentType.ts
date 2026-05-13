import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateDocumentTypeInput = Schema<"PatchedDocumentTypeRequest">;
type UpdateDocumentTypeResponse = Schema<"DocumentType">;

type UpdateDocumentTypeVariables = {
    id: string;
    data: UpdateDocumentTypeInput;
};

export function useUpdateDocumentType() {
    const queryClient = useQueryClient();

    return useMutation<UpdateDocumentTypeResponse, unknown, UpdateDocumentTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_DocumentTypes_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateDocumentTypeResponse>,
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
            queryClient.invalidateQueries({ queryKey: ["documentType", variables.id] });
        },
    });
}
