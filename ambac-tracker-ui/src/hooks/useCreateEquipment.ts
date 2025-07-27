import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreatePartTypeInput = Parameters<typeof api.api_Equipment_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_Equipment_create>>;

export const useCreateEquipment = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreatePartTypeInput>({
        mutationFn: (data) =>
            api.api_Equipment_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["equipment"] });
        },
    });
};
