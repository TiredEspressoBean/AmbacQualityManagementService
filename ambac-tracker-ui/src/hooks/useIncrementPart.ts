import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie} from "@/lib/utils.ts";

export function usePartIncrementMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_Parts_increment_create(undefined, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["parts"] });
        },
    });
}