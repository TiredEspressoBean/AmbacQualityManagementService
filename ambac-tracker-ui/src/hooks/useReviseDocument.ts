import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

interface ReviseDocumentParams {
    id: string;
    change_justification: string;
    file?: File;
    file_name?: string;
}

export function useReviseDocument() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, change_justification, file, file_name }: ReviseDocumentParams) =>
            // The endpoint is form-data, so the typed client builds the
            // multipart body. This used to hand-roll FormData and cast it past
            // the schema, which made revise dead: zod rejected the FormData
            // outright and no request was ever sent. The schema was wrong too —
            // it fell back to the whole DocumentsRequest, which has no
            // `change_justification` field, so even a corrected body would have
            // had the justification stripped before it reached the server.
            api.api_Documents_revise_create(
                {
                    change_justification,
                    ...(file ? { file } : {}),
                    ...(file && file_name ? { file_name } : {}),
                },
                { params: { id } },
            ),
        onSuccess: (_data, variables) => {
            // Invalidate document queries
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "document" && q.queryKey[1] === variables.id });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "documents" });
            // Also invalidate version history
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "document" && q.queryKey[1] === variables.id && q.queryKey[2] === "version-history" });
        },
    });
}
