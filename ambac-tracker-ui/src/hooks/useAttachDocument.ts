import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

interface AttachDocumentParams {
    /** Document id. */
    id: string;
    /** ContentType id of the target entity. */
    contentType: number;
    /** Target object's id. */
    objectId: string;
}

/**
 * Attach a document to an additional target (a secondary association via
 * DocumentLink). The primary GFK owner is never affected. Idempotent — the
 * backend revives a previously detached link rather than erroring.
 *
 * Gate the calling UI on the `add_documentlink` permission.
 */
export function useAttachDocument() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, contentType, objectId }: AttachDocumentParams) =>
            api.api_Documents_attach_create(
                { content_type: contentType, object_id: objectId },
                { params: { id } },
            ),
        onSuccess: () => {
            // A document's associations changed: refresh the doc detail + any
            // document list (both keyed under "document"), plus the per-entity
            // views where it may now appear — scoped lists and work-order QA docs.
            queryClient.invalidateQueries({ queryKey: ["document"] });
            queryClient.invalidateQueries({ queryKey: ["scope", "documents"] });
            queryClient.invalidateQueries({ queryKey: ["qa-documents"] });
        },
    });
}
