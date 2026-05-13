import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateEquipmentInput = Schema<"EquipmentsRequest">;
type CreateEquipmentResponse = Schema<"Equipments">;

export const useCreateEquipment = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateEquipmentResponse, unknown, CreateEquipmentInput>({
        mutationFn: (data) =>
            api.api_Equipment_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateEquipmentResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["equipment"] });
        },
    });
};
