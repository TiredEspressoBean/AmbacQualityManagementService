import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateCapaInput = Schema<"CAPARequest">;
type CreateCapaResponse = Schema<"CAPA">;

export const useCreateCapa = () => {
    const queryClient = useQueryClient();

    return useMutation<CreateCapaResponse, unknown, CreateCapaInput>({
        mutationFn: (data) =>
            api.api_CAPAs_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCapaResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["capas"] });
        },
    });
};
