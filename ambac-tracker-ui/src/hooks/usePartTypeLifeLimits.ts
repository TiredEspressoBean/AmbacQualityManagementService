/** Part type life limits — which life-limit definitions apply to a part type, and
 *  whether a part of that type must carry the tracking.
 *
 *  DELETE soft-archives on the backend (SecureModel.delete). The (part type,
 *  definition) pair stays unique across archived rows, so a removed link can't be
 *  created again through the API.
 */
import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { components, operations } from "@/lib/api/generated-types";

type S = components["schemas"];
export type PartTypeLifeLimit = S["PartTypeLifeLimit"];
export type LifeLimitDefinition = S["LifeLimitDefinition"];
type LinksQueries = NonNullable<operations["api_PartTypeLifeLimits_list"]["parameters"]["query"]>;

export const PART_TYPE_LIFE_LIMITS_KEY = "part-type-life-limits";
const DEFINITIONS_KEY = "life-limit-definitions";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

export const partTypeLifeLimitsOptions = (queries: LinksQueries) =>
    queryOptions({
        queryKey: [PART_TYPE_LIFE_LIMITS_KEY, queries] as const,
        queryFn: () =>
            api.api_PartTypeLifeLimits_list({ queries }) as Promise<S["PaginatedPartTypeLifeLimitList"]>,
    });

export const usePartTypeLifeLimits = (partTypeId: string) =>
    useQuery({ ...partTypeLifeLimitsOptions({ part_type: partTypeId, limit: 200 }), enabled: !!partTypeId });

export const useLifeLimitDefinitions = () =>
    useQuery(queryOptions({
        queryKey: [DEFINITIONS_KEY, { limit: 500 }] as const,
        queryFn: () =>
            api.api_LifeLimitDefinitions_list({ queries: { limit: 500, ordering: "name" } }) as Promise<
                S["PaginatedLifeLimitDefinitionList"]
            >,
    }));

function useInvalidate() {
    const queryClient = useQueryClient();
    return () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === PART_TYPE_LIFE_LIMITS_KEY });
}

export function useCreatePartTypeLifeLimit() {
    const invalidate = useInvalidate();
    return useMutation<PartTypeLifeLimit, unknown, S["PartTypeLifeLimitRequest"]>({
        mutationFn: (data) =>
            api.api_PartTypeLifeLimits_create(data, { headers: csrf() }) as Promise<PartTypeLifeLimit>,
        onSuccess: invalidate,
        meta: { successMessage: "Life limit added", suppressGlobalError: true },
    });
}

export function useUpdatePartTypeLifeLimit() {
    const invalidate = useInvalidate();
    return useMutation<PartTypeLifeLimit, unknown, { id: string; data: S["PatchedPartTypeLifeLimitRequest"] }>({
        mutationFn: ({ id, data }) =>
            api.api_PartTypeLifeLimits_partial_update(data, { params: { id }, headers: csrf() }) as Promise<PartTypeLifeLimit>,
        onSuccess: invalidate,
        meta: { errorMessage: "Couldn't update the life limit" },
    });
}

export function useDeletePartTypeLifeLimit() {
    const invalidate = useInvalidate();
    return useMutation<unknown, unknown, string>({
        mutationFn: (id) => api.api_PartTypeLifeLimits_destroy(undefined, { params: { id }, headers: csrf() }),
        onSuccess: invalidate,
        meta: { successMessage: "Life limit removed", errorMessage: "Couldn't remove the life limit" },
    });
}
