import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useDeleteDocumentType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => api.api_DocumentTypes_destroy({ params: { id } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
        },
    });
}
