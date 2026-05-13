import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateEquipmentTypeInput = Schema<"PatchedEquipmentTypeRequest">;
type UpdateEquipmentTypeResponse = Schema<"EquipmentType">;

type UpdateEquipmentTypeVariables = {
    id: string;
    data: UpdateEquipmentTypeInput;
};

export const useUpdateEquipmentType = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateEquipmentTypeResponse, unknown, UpdateEquipmentTypeVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Equipment_types_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateEquipmentTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: ["equipmenttype"],
                predicate: (query) => query.queryKey[0] === "equipmenttype",
            });
        },
    });
};
