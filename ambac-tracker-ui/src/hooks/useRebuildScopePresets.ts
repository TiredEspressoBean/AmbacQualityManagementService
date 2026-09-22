import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";
import type { Schema } from "@/lib/api/types";

type PresetsListQueries = NonNullable<
    operations["api_RebuildScopePresets_list"]["parameters"]["query"]
>;
type PresetsListResponse = components["schemas"]["PaginatedRebuildScopePresetList"];

export const rebuildScopePresetsOptions = (queries?: PresetsListQueries) =>
    queryOptions({
        queryKey: ["rebuild-scope-preset", queries] as const,
        queryFn: () =>
            api.api_RebuildScopePresets_list(
                queries ? { queries } : undefined,
            ) as Promise<PresetsListResponse>,
    });

export function useRetrieveRebuildScopePresets(queries?: PresetsListQueries) {
    return useQuery(rebuildScopePresetsOptions(queries));
}

export const rebuildScopePresetOptions = (id: string) =>
    queryOptions({
        queryKey: ["rebuild-scope-preset", id] as const,
        queryFn: () =>
            api.api_RebuildScopePresets_retrieve({
                params: { id },
            }) as Promise<Schema<"RebuildScopePreset">>,
    });

export function useRetrieveRebuildScopePreset(id: string, options?: { enabled?: boolean }) {
    return useQuery({
        ...rebuildScopePresetOptions(id),
        enabled: options?.enabled ?? !!id,
    });
}

function invalidate(queryClient: ReturnType<typeof useQueryClient>) {
    queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] === "rebuild-scope-preset",
    });
}

export function useCreateRebuildScopePreset() {
    const queryClient = useQueryClient();
    return useMutation<
        Schema<"RebuildScopePreset">,
        unknown,
        Schema<"RebuildScopePresetRequest">
    >({
        mutationFn: (data) =>
            api.api_RebuildScopePresets_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RebuildScopePreset">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useUpdateRebuildScopePreset() {
    const queryClient = useQueryClient();
    return useMutation<
        Schema<"RebuildScopePreset">,
        unknown,
        { id: string; data: Schema<"PatchedRebuildScopePresetRequest"> }
    >({
        mutationFn: ({ id, data }) =>
            api.api_RebuildScopePresets_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RebuildScopePreset">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useDeleteRebuildScopePreset() {
    const queryClient = useQueryClient();
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) =>
            api.api_RebuildScopePresets_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => invalidate(queryClient),
    });
}
