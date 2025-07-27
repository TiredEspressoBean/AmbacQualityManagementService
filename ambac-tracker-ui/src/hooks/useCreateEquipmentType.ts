import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateEquipmentTypeInput = Parameters<typeof api.api_Equipment_types_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_Equipment_types_create>>;

export const useCreateEquipmentType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreateEquipmentTypeInput>({
        mutationFn: (data) =>
            api.api_Equipment_types_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
