import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils";

type CreateThreeDModelInput = Parameters<typeof api.api_ThreeDModels_create>[0];
type CreateThreeDModelResponse = Awaited<ReturnType<typeof api.api_ThreeDModels_create>>;

export function useCreateThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation<CreateThreeDModelResponse, unknown, CreateThreeDModelInput>({
        mutationFn: (data) =>
            api.api_ThreeDModels_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threeDModel"] });
        },
    });
};
