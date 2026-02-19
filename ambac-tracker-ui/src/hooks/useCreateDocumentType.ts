import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export function useCreateDocumentType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: any) => api.api_DocumentTypes_create({ body: data }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
        },
    });
}
