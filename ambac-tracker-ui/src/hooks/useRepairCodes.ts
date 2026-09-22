import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated.ts";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";
import type { Schema } from "@/lib/api/types";

type RepairCodesListQueries = NonNullable<
    operations["api_RepairCodes_list"]["parameters"]["query"]
>;
type RepairCodesListResponse = components["schemas"]["PaginatedRepairCodeList"];

export const repairCodesOptions = (queries?: RepairCodesListQueries) =>
    queryOptions({
        queryKey: ["repair-code", queries] as const,
        queryFn: () =>
            api.api_RepairCodes_list(
                queries ? { queries } : undefined,
            ) as Promise<RepairCodesListResponse>,
    });

export function useRetrieveRepairCodes(queries?: RepairCodesListQueries) {
    return useQuery(repairCodesOptions(queries));
}

export const repairCodeOptions = (id: string) =>
    queryOptions({
        queryKey: ["repair-code", id] as const,
        queryFn: () =>
            api.api_RepairCodes_retrieve({ params: { id } }) as Promise<Schema<"RepairCode">>,
    });

export function useRetrieveRepairCode(id: string, options?: { enabled?: boolean }) {
    return useQuery({ ...repairCodeOptions(id), enabled: options?.enabled ?? !!id });
}

// One invalidation predicate for every mutation below: the list and the detail share
// the "repair-code" key root, and a stale list after an edit is the classic way a save
// looks like it did nothing.
function invalidate(queryClient: ReturnType<typeof useQueryClient>) {
    queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "repair-code" });
}

export function useCreateRepairCode() {
    const queryClient = useQueryClient();
    return useMutation<Schema<"RepairCode">, unknown, Schema<"RepairCodeRequest">>({
        mutationFn: (data) =>
            api.api_RepairCodes_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RepairCode">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useUpdateRepairCode() {
    const queryClient = useQueryClient();
    return useMutation<
        Schema<"RepairCode">,
        unknown,
        { id: string; data: Schema<"PatchedRepairCodeRequest"> }
    >({
        mutationFn: ({ id, data }) =>
            api.api_RepairCodes_partial_update(data, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }) as Promise<Schema<"RepairCode">>,
        onSuccess: () => invalidate(queryClient),
    });
}

export function useDeleteRepairCode() {
    const queryClient = useQueryClient();
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) =>
            api.api_RepairCodes_destroy(undefined, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => invalidate(queryClient),
    });
}
