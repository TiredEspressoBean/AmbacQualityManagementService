import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateEquipmentInput = Parameters<typeof api.api_Equipment_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateEquipmentConfig = Parameters<typeof api.api_Equipment_partial_update>[1];
type UpdateEquipmentParams = UpdateEquipmentConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateEquipmentResponse = Awaited<ReturnType<typeof api.api_Equipment_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateEquipmentVariables = {
    id: UpdateEquipmentParams["id"];   // number
    data: UpdateEquipmentInput;        // exactly the patched-part payload
};

export const useUpdateEquipment = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateEquipmentResponse, unknown, UpdateEquipmentVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Equipment_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            // Invalidate both singular (detail) and plural (list) queries
            queryClient.invalidateQueries({
                predicate: (query) =>
                    query.queryKey[0] === "equipment" || query.queryKey[0] === "equipments",
            });
        },
    });
};
