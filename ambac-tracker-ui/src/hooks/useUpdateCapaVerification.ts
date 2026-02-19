import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";

type UpdateCapaVerificationInput = Parameters<typeof api.api_CapaVerifications_partial_update>[1];
type UpdateCapaVerificationResponse = Awaited<ReturnType<typeof api.api_CapaVerifications_partial_update>>;

export const useUpdateCapaVerification = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCapaVerificationResponse, unknown, { id: string; data: UpdateCapaVerificationInput }>({
        mutationFn: ({ id, data }) =>
            api.api_CapaVerifications_partial_update({ id }, data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-verifications"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
