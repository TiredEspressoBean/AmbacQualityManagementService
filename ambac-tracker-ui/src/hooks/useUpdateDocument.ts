import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateDocumentInput = Parameters<typeof api.api_Documents_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateDocumentConfig = Parameters<typeof api.api_Documents_partial_update>[1];
type UpdateDocumentParams = UpdateDocumentConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateDocumentResponse = Awaited<ReturnType<typeof api.api_Documents_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateDocumentVariables = {
    id: UpdateDocumentParams["id"];   // number
    data: UpdateDocumentInput;        // exactly the patched-part payload
};

export const useUpdateDocument = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateDocumentResponse, unknown, UpdateDocumentVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Documents_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["document"],
                predicate: (query) => query.queryKey[0] === "equipment",
            });
        },
    });
};
