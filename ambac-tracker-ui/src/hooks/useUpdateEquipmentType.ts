import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// 1️⃣ Infer the exact input (body) that the partial-update endpoint wants:
type UpdateEquipmentTypeInput = Parameters<typeof api.api_Equipment_types_partial_update>[0];

// 2️⃣ Infer the shape of the `params` object:
type UpdateEquipmentTypeConfig = Parameters<typeof api.api_Equipment_types_partial_update>[1];
type UpdateEquipmentTypeParams = UpdateEquipmentTypeConfig["params"];

// 3️⃣ Infer the response type, if you need it:
type UpdateEquipmentTypeResponse = Awaited<ReturnType<typeof api.api_Equipment_types_partial_update>>;

// 4️⃣ Compose the variables your hook will accept:
type UpdateEquipmentTypeVariables = {
    id: UpdateEquipmentTypeParams["id"];   // number
    data: UpdateEquipmentTypeInput;        // exactly the patched-part payload
};

export const useUpdateEquipmentType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateEquipmentTypeResponse, unknown, UpdateEquipmentTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Equipment_types_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["equipmenttype"],
                predicate: (query) => query.queryKey[0] === "equipmenttype",
            });
        },
    });
};
