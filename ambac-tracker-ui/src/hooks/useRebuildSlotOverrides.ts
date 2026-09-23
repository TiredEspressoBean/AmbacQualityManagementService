import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

/**
 * An override is a deviation from the computed rebuild plan, so every mutation has to
 * invalidate the PLAN as well as the override list — the plan is recomputed server-side
 * and is what the screen actually renders. Invalidating only the overrides would leave
 * a saved decision invisible until a reload.
 */
function invalidate(queryClient: ReturnType<typeof useQueryClient>) {
    queryClient.invalidateQueries({
        predicate: (q) =>
            q.queryKey[0] === "rebuild-slot-override" || q.queryKey[0] === "rebuildPlan",
    });
}

export function useCreateSlotOverride() {
    const queryClient = useQueryClient();
    return useMutation<
        Schema<"RebuildSlotOverride">,
        unknown,
        Schema<"RebuildSlotOverrideRequest">
    >({
        mutationFn: (data) =>
            api.api_RebuildSlotOverrides_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RebuildSlotOverride">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useUpdateSlotOverride() {
    const queryClient = useQueryClient();
    return useMutation<
        Schema<"RebuildSlotOverride">,
        unknown,
        { id: string; data: Schema<"PatchedRebuildSlotOverrideRequest"> }
    >({
        mutationFn: ({ id, data }) =>
            api.api_RebuildSlotOverrides_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RebuildSlotOverride">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useDeleteSlotOverride() {
    const queryClient = useQueryClient();
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) =>
            api.api_RebuildSlotOverrides_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => invalidate(queryClient),
    });
}
