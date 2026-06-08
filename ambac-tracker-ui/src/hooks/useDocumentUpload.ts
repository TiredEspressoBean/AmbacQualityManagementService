/**
 * Upload a File to `/api/Documents/` and return the persisted Documents row.
 *
 * Used by the operator-runtime capture nodes (PhotoCapture, FileCapture,
 * VideoCapture in future) to land a real Documents FK on the
 * SubstepResponse instead of just a filename string. Backend already
 * accepts `document_id` in the substep-submit capture payload — this
 * hook produces that id.
 *
 * Goes through the existing DocumentViewSet's create endpoint which uses
 * MultiPartParser; STORAGES routing (S3 vs filesystem) is handled
 * tenant-side in settings.py.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

const csrfHeaders = (): HeadersInit => {
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
     *  without the reverse GFK pointing back). */
    contentType?: string;
    objectId?: string;
};

export function useDocumentUpload() {
    const qc = useQueryClient();
    return useMutation<UploadedDocument, unknown, UploadInput>({
        mutationFn: async ({ file, contentType, objectId }) => {
            const form = new FormData();
            form.append("file", file);
            form.append("file_name", file.name);
            if (contentType) form.append("content_type", contentType);
            if (objectId) form.append("object_id", objectId);

            const res = await fetch("/api/Documents/", {
                method: "POST",
                credentials: "include",
                headers: csrfHeaders(),
                body: form,
            });
            if (!res.ok) {
                let detail = "Upload failed";
                try {
                    const body = await res.json();
                    detail = body.detail ?? JSON.stringify(body);
                } catch {
                    /* ignore */
                }
                throw new Error(`${res.status}: ${detail}`);
            }
            const body = await res.json();
            return {
                document_id: String(body.id),
                file_name: String(body.file_name ?? file.name),
                file_url: body.file_url,
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
