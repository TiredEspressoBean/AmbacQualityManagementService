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
        mutationFn: async ({ id, change_justification, file, file_name }: ReviseDocumentParams) => {
            const formData = new FormData();
            formData.append("change_justification", change_justification);
            if (file) {
                formData.append("file", file);
                if (file_name) {
                    formData.append("file_name", file_name);
                }
            }

            // Use the generated API client's revise endpoint
            return api.api_Documents_revise_create({
                id,
                data: formData as any,
            });
        },
        onSuccess: (_data, variables) => {
            // Invalidate document queries
            queryClient.invalidateQueries({ queryKey: ["document", variables.id] });
            queryClient.invalidateQueries({ queryKey: ["documents"] });
            // Also invalidate version history
            queryClient.invalidateQueries({ queryKey: ["document", variables.id, "version-history"] });
        },
    });
}
