import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

interface DetachDocumentParams {
    /** Document id. */
    id: string;
    /** ContentType id of the target entity. */
    contentType: number;
    /** Target object's id. */
    objectId: string;
}

/**
 * Remove a secondary association (DocumentLink) from a document. Soft-deletes
 * the link; a no-op if none exists. The primary GFK owner is never affected.
 *
 * Gate the calling UI on the `delete_documentlink` permission.
 */
export function useDetachDocument() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, contentType, objectId }: DetachDocumentParams) =>
            api.api_Documents_detach_create(
                { content_type: contentType, object_id: objectId },
                { params: { id } },
            ),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["document"] });
            queryClient.invalidateQueries({ queryKey: ["scope", "documents"] });
            queryClient.invalidateQueries({ queryKey: ["qa-documents"] });
        },
    });
}
