import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

type UpdateThreeDModelInput = Schema<"PatchedThreeDModelRequest">;
type UpdateThreeDModelResponse = Schema<"ThreeDModel">;

type UpdateThreeDModelVariables = {
    id: string;
    data: UpdateThreeDModelInput;
};

export function useUpdateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<UpdateThreeDModelResponse, unknown, UpdateThreeDModelVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ThreeDModels_partial_update(data as never, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateThreeDModelResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threeDModel"] });
        },
    });
}
