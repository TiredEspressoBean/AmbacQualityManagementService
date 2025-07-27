import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateSampling_rulesInput = Parameters<typeof api.api_Sampling_rules_create>[0];

type CreatePartResponse = Awaited<ReturnType<typeof api.api_Sampling_rules_create>>;

export const useCreateSamplingRule = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartResponse, unknown, CreateSampling_rulesInput>({
        mutationFn: (data) =>
            api.api_Sampling_rules_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["sampling-rule"] });
        },
    });
};
