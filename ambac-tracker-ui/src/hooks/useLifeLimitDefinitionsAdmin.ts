/** Life limit definitions as their own table: what a part can wear out by (cycles,
 *  hours, shelf life) and the soft / hard limits. Part types link to them on their
 *  own form. Edits are versioned on the backend. */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";

type S = components["schemas"];
export type LifeLimitDefinition = S["LifeLimitDefinition"];
type Queries = NonNullable<operations["api_LifeLimitDefinitions_list"]["parameters"]["query"]>;

// Same root as the part-type panel's definition list, so edits here refresh it.
export const LIFE_LIMIT_DEFINITIONS_KEY = "life-limit-definitions";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

export const lifeLimitDefinitionsOptions = (queries?: Queries) =>
    queryOptions({
        queryKey: [LIFE_LIMIT_DEFINITIONS_KEY, queries] as const,
        queryFn: () =>
            api.api_LifeLimitDefinitions_list(queries ? { queries } : undefined) as Promise<S["PaginatedLifeLimitDefinitionList"]>,
    });

export const useLifeLimitDefinitionsList = (queries?: Queries) => useQuery(lifeLimitDefinitionsOptions(queries));

export const lifeLimitDefinitionOptions = (id: string) =>
    queryOptions({
        queryKey: [LIFE_LIMIT_DEFINITIONS_KEY, "detail", id] as const,
        queryFn: () => api.api_LifeLimitDefinitions_retrieve({ params: { id } }) as Promise<LifeLimitDefinition>,
    });

export const useLifeLimitDefinition = (id: string) => useQuery({ ...lifeLimitDefinitionOptions(id), enabled: !!id });

function useInvalidate() {
    const queryClient = useQueryClient();
    return () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === LIFE_LIMIT_DEFINITIONS_KEY });
}

export function useCreateLifeLimitDefinition() {
    const invalidate = useInvalidate();
    return useMutation<LifeLimitDefinition, unknown, S["LifeLimitDefinitionRequest"]>({
        mutationFn: (data) => api.api_LifeLimitDefinitions_create(data, { headers: csrf() }) as Promise<LifeLimitDefinition>,
        onSuccess: invalidate,
    });
}

export function useUpdateLifeLimitDefinition() {
    const invalidate = useInvalidate();
    return useMutation<LifeLimitDefinition, unknown, { id: string; data: S["PatchedLifeLimitDefinitionRequest"] }>({
        mutationFn: ({ id, data }) =>
            api.api_LifeLimitDefinitions_partial_update(data, { params: { id }, headers: csrf() }) as Promise<LifeLimitDefinition>,
        onSuccess: invalidate,
    });
}

export function useDeleteLifeLimitDefinition() {
    const invalidate = useInvalidate();
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) => api.api_LifeLimitDefinitions_destroy(undefined, { params: { id }, headers: csrf() }),
        onSuccess: invalidate,
    });
}
