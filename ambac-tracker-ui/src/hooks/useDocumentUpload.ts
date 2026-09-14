/**
 * Upload a File to `/api/Documents/` and return the persisted Documents row.
 *
 * Used by the operator-runtime capture nodes (PhotoCapture, FileCapture,
 * VideoCapture in future) to land a real Documents FK on the
 * SubstepResponse instead of just a filename string. Backend already
 * accepts `document_id` in the substep-submit capture payload — this
 * hook produces that id.
 *
 * Goes through DocumentViewSet's create endpoint via the generated client —
 * the endpoint is declared multipart, so `api_Documents_create` carries
 * requestFormat "form-data" and builds the body itself. STORAGES routing
 * (S3 vs filesystem) is handled tenant-side in settings.py.
 *
 * This was a hand-rolled `fetch` until the multipart path was re-tested:
 * uploads through the Vite dev proxy used to hang or reset, which looked like
 * runserver being unable to take multipart POSTs. The cause was the proxy
 * (`agent: false` deadlocking large bodies on Windows loopback, plus
 * runserver keep-alive RSTs) — see the notes in vite.config.ts — and it is
 * fixed. Re-measured at 0.5 MB / 8 MB / 25 MB, both through the proxy and
 * direct to :8000: typed client and raw fetch behave identically, including
 * well past FILE_UPLOAD_MAX_MEMORY_SIZE (2.5 MB) where Django streams to a
 * temp file.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Plain record rather than fetch's HeadersInit: these now go to axios via the
// generated client, which types headers as its own RawAxiosHeaders shape.
const csrfHeaders = (): Record<string, string> => {
    const token = getCookie("csrftoken");
    return token ? { "X-CSRFToken": token } : {};
};

export type UploadedDocument = {
    document_id: string;
    file_name: string;
    file_url?: string;
    is_image: boolean;
};

type UploadInput = {
    file: File;
    /** Optional GenericForeignKey wiring. When unset the Documents row
     *  is created as an orphan (which is fine — operator captures can
     *  attach themselves to a SubstepResponse via value_document FK
     *  without the reverse GFK pointing back).
     *
     *  `contentType` is a ContentType **pk**, not a label — it was typed
     *  `string` here while the API declares `content_type: number`. Nothing
     *  currently passes either field (all three callers send just `{ file }`),
     *  so the mismatch was never hit; the raw fetch would have stringified a
     *  label straight into the form body and let DRF reject it. */
    contentType?: number;
    objectId?: string;
};

export function useDocumentUpload() {
    const qc = useQueryClient();
    return useMutation<UploadedDocument, unknown, UploadInput>({
        mutationFn: async ({ file, contentType, objectId }) => {
            // `api_Documents_create` is generated with requestFormat "form-data",
            // so the typed client builds the multipart body itself — no hand-rolled
            // FormData, and the response is schema-checked like every other call.
            const body = await api.api_Documents_create(
                {
                    file,
                    file_name: file.name,
                    ...(contentType ? { content_type: contentType } : {}),
                    ...(objectId ? { object_id: objectId } : {}),
                },
                { headers: csrfHeaders() },
            );
            return {
                document_id: String(body.id),
                file_name: String(body.file_name ?? file.name),
                file_url: body.file_url ?? undefined,
                is_image: Boolean(body.is_image),
            };
        },
        onSuccess: () => {
            // Refresh Documents list queries so newly-uploaded files
            // appear in any attachment pickers.
            qc.invalidateQueries({ predicate: (q) => q.queryKey[0] === "documents" });
        },
    });
}
