import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateEquipmentInput = Schema<"PatchedEquipmentsRequest">;
type UpdateEquipmentResponse = Schema<"Equipments">;

type UpdateEquipmentVariables = {
    id: string;
    data: UpdateEquipmentInput;
};

export const useUpdateEquipment = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateEquipmentResponse, unknown, UpdateEquipmentVariables>({
        mutationFn: ({ id, data }) =>
            api.api_Equipment_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateEquipmentResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({
                predicate: (query) =>
                    query.queryKey[0] === "equipment" || query.queryKey[0] === "equipments",
            });
        },
    });
};
