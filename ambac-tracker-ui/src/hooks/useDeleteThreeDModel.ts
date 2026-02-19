import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/generated.ts"
import { getCookie } from "@/lib/utils.ts";

export function useDeleteThreeDModel() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_ThreeDModels_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["threeDModel"] });
        },
    });
};
