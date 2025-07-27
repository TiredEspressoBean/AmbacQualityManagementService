import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

export function useDeleteEquipment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: number) =>
            api.api_Equipment_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["equipment", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["equipment"] });
        },
    });
}
