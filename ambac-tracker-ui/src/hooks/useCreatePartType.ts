import { api } from "@/lib/api/generated";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreatePartTypeInput = Schema<"PartTypesRequest">;
type CreatePartTypeResponse = Schema<"PartTypes">;

export const useCreatePartType = () => {
    const queryClient = useQueryClient();

    return useMutation<CreatePartTypeResponse, unknown, CreatePartTypeInput>({
        mutationFn: (data) =>
            api.api_PartTypes_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreatePartTypeResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parttype"] });
        },
    });
};
