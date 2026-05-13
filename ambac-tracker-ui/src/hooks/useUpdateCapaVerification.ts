import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateCapaVerificationInput = Schema<"PatchedCapaVerificationRequest">;
type UpdateCapaVerificationResponse = Schema<"CapaVerification">;

export const useUpdateCapaVerification = () => {
    const queryClient = useQueryClient();

    return useMutation<UpdateCapaVerificationResponse, unknown, { id: string; data: UpdateCapaVerificationInput }>({
        mutationFn: ({ id, data }) =>
            api.api_CapaVerifications_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateCapaVerificationResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capa-verifications"] });
            queryClient.invalidateQueries({ queryKey: ["capa"] });
        },
    });
};
