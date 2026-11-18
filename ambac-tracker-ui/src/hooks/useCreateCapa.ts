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
            api.api_CAPAs_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateCapaResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "capas" });
            // A CAPA from an NCR's reports marks that NCR CAPA raised.
            queryClient.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith("ncr") });
        },
    });
};
