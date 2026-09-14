import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils.ts";

// Invalidation-only helper (not a real queryOptions — no queryFn needed).
const equipmentTypeKeyOptions = () => ({ queryKey: ["equipment-type"] as const });

export function useDeleteEquipmentType() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) =>
            api.api_Equipment_types_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        mutationKey: ["equipment-types", "delete"],
        onSuccess: () => {
            queryClient.invalidateQueries(equipmentTypeKeyOptions());
        },
    });
}
