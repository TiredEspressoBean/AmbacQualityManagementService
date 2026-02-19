import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Infer types from the API
type UpdateDocumentTypeInput = Parameters<typeof api.api_DocumentTypes_partial_update>[0];
type UpdateDocumentTypeConfig = Parameters<typeof api.api_DocumentTypes_partial_update>[1];
type UpdateDocumentTypeParams = UpdateDocumentTypeConfig["params"];
type UpdateDocumentTypeResponse = Awaited<ReturnType<typeof api.api_DocumentTypes_partial_update>>;

type UpdateDocumentTypeVariables = {
    id: UpdateDocumentTypeParams["id"];
    data: UpdateDocumentTypeInput;
};

export function useUpdateDocumentType() {
    const queryClient = useQueryClient();

    return useMutation<UpdateDocumentTypeResponse, unknown, UpdateDocumentTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_DocumentTypes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ["documentTypes"] });
            queryClient.invalidateQueries({ queryKey: ["documentType", variables.id] });
        },
    });
}
