import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

type CreateInput = Parameters<typeof api.api_integrations_create>[0];
type CreateResponse = Awaited<ReturnType<typeof api.api_integrations_create>>;

export const useCreateIntegration = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateResponse, unknown, CreateInput>({
        mutationFn: (data) =>
            api.api_integrations_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["integrations-catalog"] });
            queryClient.invalidateQueries({ queryKey: ["integration"] });
        },
    });
};
