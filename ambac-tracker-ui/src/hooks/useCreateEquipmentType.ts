import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateEquipmentTypeInput = Schema<"EquipmentTypeRequest">;
type CreateEquipmentTypeResponse = Schema<"EquipmentType">;

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const parttypeKeyOptions = () => ({ queryKey: ["parttype"] as const });

export const useCreateEquipmentType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateEquipmentTypeResponse, unknown, CreateEquipmentTypeInput>({
        mutationFn: (data) =>
            api.api_Equipment_types_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateEquipmentTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(parttypeKeyOptions());
        },
    });
};
