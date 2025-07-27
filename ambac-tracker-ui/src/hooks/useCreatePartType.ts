import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreatePartTypeInput = Parameters<typeof api.api_PartTypes_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_PartTypes_create>>;

export const useCreatePartType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreatePartTypeInput>({
        mutationFn: (data) =>
            api.api_PartTypes_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
