import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type CreateCapaVerificationInput = Parameters<typeof api.api_CapaVerifications_create>[0];
type CreateCapaVerificationResponse = Awaited<ReturnType<typeof api.api_CapaVerifications_create>>;

export const useCreateCapaVerification = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaVerificationResponse, unknown, CreateCapaVerificationInput>({
        mutationFn: (data) =>
            api.api_CapaVerifications_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-verifications"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
