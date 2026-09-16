import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

// Derived from the zodios client, not from openapi-typescript's Schema<>.
// The two generators disagree on multipart file fields -- Schema<> types
// `file` as a string, the client as a File -- and the client is right for a
// form-data upload. Typing it from Schema<> and casting the mismatch away
// let a caller pass a string that zod would reject at runtime.
type UpdateDocumentInput = Parameters<typeof api.api_Documents_partial_update>[0];
type UpdateDocumentResponse = Schema<"Documents">;

type UpdateDocumentVariables = {
    id: string;
    data: UpdateDocumentInput;
};

export const useUpdateDocument = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateDocumentResponse, unknown, UpdateDocumentVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Documents_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateDocumentResponse>,
        onSuccess: () => {
            // Updating a document invalidated NOTHING before this: the filter
            // combined queryKey ["document"] with a predicate requiring
            // queryKey[0] === "equipment", and TanStack ANDs those two, so it
            // could never match. The equipment predicate was copy-paste from an
            // equipment hook. Both the detail key ("document") and the list key
            // ("documents") are refreshed, which is what the update should do.
            queryClient.invalidateQueries({
                predicate: (q) => q.queryKey[0] === "document" || q.queryKey[0] === "documents",
            });
        },
    });
};
