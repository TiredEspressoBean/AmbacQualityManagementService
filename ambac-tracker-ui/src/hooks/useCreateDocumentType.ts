import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateDocumentTypeInput = Schema<"DocumentTypeRequest">;
type CreateDocumentTypeResponse = Schema<"DocumentType">;

export function useCreateDocumentType() {
    const queryClient = useQueryClient();

    return useMutation<CreateDocumentTypeResponse, unknown, CreateDocumentTypeInput>({
        mutationFn: (data) =>
            api.api_DocumentTypes_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateDocumentTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
        },
    });
}
