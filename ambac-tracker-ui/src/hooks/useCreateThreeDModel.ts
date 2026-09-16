import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

// Derived from the zodios client, not from openapi-typescript's Schema<>.
// The two generators disagree on multipart file fields -- Schema<> types
// `file` as a string, the client as a File -- and the client is right for a
// form-data upload. Typing it from Schema<> and casting the mismatch away
// let a caller pass a string that zod would reject at runtime.
type CreateThreeDModelInput = Parameters<typeof api.api_ThreeDModels_create>[0];
type CreateThreeDModelResponse = Schema<"ThreeDModel">;

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const threeDModelKeyOptions = () => ({ queryKey: ["threeDModel"] as const });

export function useCreateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<CreateThreeDModelResponse, unknown, CreateThreeDModelInput>({
        mutationFn: (data) =>
            api.api_ThreeDModels_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<CreateThreeDModelResponse>,
        onSuccess: () => {
            queryClient.invalidateQueries(threeDModelKeyOptions());
        },
    });
}
