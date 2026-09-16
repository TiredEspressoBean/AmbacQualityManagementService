import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

// Derived from the zodios client, not from openapi-typescript's Schema<>.
// The two generators disagree on multipart file fields -- Schema<> types
// `file` as a string, the client as a File -- and the client is right for a
// form-data upload. Typing it from Schema<> and casting the mismatch away
// let a caller pass a string that zod would reject at runtime.
type UpdateThreeDModelInput = Parameters<typeof api.api_ThreeDModels_partial_update>[0];
type UpdateThreeDModelResponse = Schema<"ThreeDModel">;

type UpdateThreeDModelVariables = {
    id: string;
    data: UpdateThreeDModelInput;
};

export function useUpdateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<UpdateThreeDModelResponse, unknown, UpdateThreeDModelVariables>({
        mutationFn: ({ id, data }) =>
            api.api_ThreeDModels_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<UpdateThreeDModelResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "threeDModel" });
        },
    });
}
