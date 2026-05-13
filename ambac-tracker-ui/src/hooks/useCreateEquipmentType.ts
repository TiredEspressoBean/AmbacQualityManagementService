import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateEquipmentTypeInput = Schema<"EquipmentTypeRequest">;
type CreateEquipmentTypeResponse = Schema<"EquipmentType">;

export const useCreateEquipmentType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateEquipmentTypeResponse, unknown, CreateEquipmentTypeInput>({
        mutationFn: (data) =>
            api.api_Equipment_types_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateEquipmentTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
