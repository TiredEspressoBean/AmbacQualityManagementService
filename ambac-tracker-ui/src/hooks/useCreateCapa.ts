import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateCapaInput = Parameters<typeof api.api_CAPAs_create>[0];
type CreateCapaResponse = Awaited<ReturnType<typeof api.api_CAPAs_create>>;

export const useCreateCapa = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaResponse, unknown, CreateCapaInput>({
        mutationFn: (data) =>
            api.api_CAPAs_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capas"] });
        },
    });
};