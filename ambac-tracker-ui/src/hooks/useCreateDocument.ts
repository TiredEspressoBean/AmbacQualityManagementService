import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateDocumentInput = Schema<"DocumentsRequest">;
type CreateDocumentResponse = Schema<"Documents">;

export const useCreateDocument = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateDocumentResponse, unknown, CreateDocumentInput>({
        mutationFn: (data) =>
            api.api_Documents_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateDocumentResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["document"] });
        },
    });
};
