import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateCapaVerificationInput = Schema<"CapaVerificationRequest">;
type CreateCapaVerificationResponse = Schema<"CapaVerification">;

export const useCreateCapaVerification = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaVerificationResponse, unknown, CreateCapaVerificationInput>({
        mutationFn: (data) =>
            api.api_CapaVerifications_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCapaVerificationResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capa-verifications" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capa" });
        },
    });
};
