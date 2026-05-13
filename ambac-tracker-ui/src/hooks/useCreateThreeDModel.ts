import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type CreateThreeDModelInput = Schema<"ThreeDModelRequest">;
type CreateThreeDModelResponse = Schema<"ThreeDModel">;

export function useCreateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<CreateThreeDModelResponse, unknown, CreateThreeDModelInput>({
        mutationFn: (data) =>
            api.api_ThreeDModels_create(data as never, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateThreeDModelResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threeDModel"] });
        },
    });
}
