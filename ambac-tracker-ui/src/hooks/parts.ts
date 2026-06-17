/**
 * Parts API — consolidated hooks file.
 *
 * Owns every read and mutation for the `/api/Parts/...` endpoints. Mutations
 * invalidate via the local `partsKeys` namespace so cache-key drift between
 * factory and invalidator is structurally impossible — both reference the
 * same symbol.
 *
 * For the factory/hook pattern rules (no explicit `useQuery<X>` generic,
 * `Omit<ReturnType<typeof xOptions>, ...>` for options, etc.), see the
 * doc block on `partsOptions` below. The full rationale lives in this file
 * because mutation/invalidation coupling is part of the contract too.
 *
 * Convention for cache keys:
 *
 *   partsKeys.all                    → ["parts"]
 *   partsKeys.list(queries, config)  → ["parts", "list", queries, config]
 *   partsKeys.detail(id)             → ["parts", "detail", id]
 *   partsKeys.metadata()             → ["parts", "metadata"]
 *   partsKeys.traveler(id)           → ["parts", "traveler", id]
 *
 * Every key starts with the literal "parts" so a single predicate-match
 * invalidation (`predicate: q => q.queryKey[0] === "parts"`) or a
 * `partsKeys.all` prefix-match invalidation nukes every Parts query.
 *
 * Historical bug this prevents: before consolidation, the list factory used
 * ["part", ...] (singular) but mutations invalidated ["parts"] (plural).
 * The list never invalidated after bulk operations — silent stale UI.
 */

import { useQuery, useMutation, useQueryClient, queryOptions, mutationOptions, type QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { components, operations } from "@/lib/api/generated-types";
import type { Schema } from "@/lib/api/types";
import { getCookie } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

type PartsListQueries = NonNullable<operations["api_Parts_list"]["parameters"]["query"]>;
type PartsListResponse = components["schemas"]["PaginatedPartsList"];
type PartsResponse = Schema<"Parts">;
type TravelerResponse = Schema<"PartTravelerResponse">;

type CreatePartInput = Schema<"PartsRequest">;
type CreatePartResponse = Schema<"Parts">;

type UpdatePartInput = Schema<"PatchedPartsRequest">;
type UpdatePartResponse = Schema<"Parts">;
type UpdatePartVariables = { id: string; data: UpdatePartInput };

type ListHookConfig = { headers?: Record<string, string> };

// =============================================================================
// Cache keys — single source of truth for the Parts namespace.
// =============================================================================

export const partsKeys = {
    all: ["parts"] as const,
    list: (queries?: PartsListQueries, config?: ListHookConfig) =>
        ["parts", "list", queries, config] as const,
    detail: (query: Parameters<typeof api.api_Parts_retrieve>[0]) =>
        ["parts", "detail", query] as const,
    metadata: () => ["parts", "metadata"] as const,
    traveler: (id: string) => ["parts", "traveler", id] as const,
};

// =============================================================================
// Query option factories
// =============================================================================

/**
 * Canonical list-style hook factory.
 *
 * Rules (apply to every factory below):
 *   1. No explicit `useQuery<X, Error>` generic at the call site — spreading
 *      a queryOptions result with explicit generics kills inference and
 *      consumers see `NoInfer<TQueryFnData>` placeholder types.
 *   2. Runtime options typed as `Omit<ReturnType<typeof xOptions>, "queryKey"
 *      | "queryFn">` — derives from the factory's own return type.
 *   3. `as never` cast on `{ queries, ...config }` bridges zodios's
 *      deep-readonly Args vs the strict OpenAPI queries shape.
 *   4. `as Promise<XResponse>` is the single contract for the return type.
 */
export const partsOptions = (queries?: PartsListQueries, config?: ListHookConfig) =>
    queryOptions({
        queryKey: partsKeys.list(queries, config),
        queryFn: () =>
            api.api_Parts_list(
                (queries || config ? { queries, ...config } : undefined) as never,
            ) as Promise<PartsListResponse>,
    });

export const partsMetadataOptions = () =>
    queryOptions({
        queryKey: partsKeys.metadata(),
        queryFn: () => api.api_Parts_metadata_retrieve(),
    });

export const retrievePartOptions = (query: Parameters<typeof api.api_Parts_retrieve>[0]) =>
    queryOptions({
        queryKey: partsKeys.detail(query),
        queryFn: () => api.api_Parts_retrieve(query) as Promise<PartsResponse>,
    });

export const partTravelerOptions = (partId: string) =>
    queryOptions({
        queryKey: partsKeys.traveler(partId),
        // eslint-disable-next-line local/no-double-cast-via-unknown -- api_Parts_traveler_retrieve returns an opaque type; Schema<"PartTravelerResponse"> matches runtime shape
        queryFn: () => api.api_Parts_traveler_retrieve({ params: { id: partId } }) as unknown as Promise<TravelerResponse>,
    });

// =============================================================================
// Read hooks
// =============================================================================

export function useRetrieveParts(
    queries?: PartsListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof partsOptions>, "queryKey" | "queryFn">,
) {
    return useQuery({ ...partsOptions(queries, config), ...options });
}

export function useRetrievePart(
    query: Parameters<typeof api.api_Parts_retrieve>[0],
    options?: { enabled?: boolean },
) {
    return useQuery({ ...retrievePartOptions(query), enabled: options?.enabled ?? true });
}

export function usePartTraveler(partId: string, options?: { enabled?: boolean }) {
    return useQuery({
        ...partTravelerOptions(partId),
        enabled: (options?.enabled ?? true) && !!partId,
    });
}

// =============================================================================
// Mutation namespace + helpers
// =============================================================================

/**
 * Mutation keys. Used by `useIsMutating` / `useMutationState` to track parts
 * mutations from anywhere in the app without prop drilling.
 */
export const partsMutationKeys = {
    create: ["parts", "create"] as const,
    update: ["parts", "update"] as const,
    increment: ["parts", "increment"] as const,
    bulkIncrement: ["parts", "bulk-increment"] as const,
    bulkRollback: ["parts", "bulk-rollback"] as const,
    bulkSetStatus: ["parts", "bulk-set-status"] as const,
    splitFromLot: ["parts", "split-from-lot"] as const,
    advanceLot: ["parts", "advance-lot"] as const,
    completeStep: ["parts", "complete-step"] as const,
};

export type PartSplitReason =
    | "quarantine"
    | "rework"
    | "scrap";

type SplitFromLotVariables = {
    id: string;
    reason: PartSplitReason;
    rework_target_step_id?: string;
    notes?: string;
};

type AdvanceLotVariables = {
    work_order_id: string;
    step_id: string;
};

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

const invalidateAllParts = (queryClient: QueryClient) =>
    queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] === partsKeys.all[0],
    });

type BulkSetStatusVariables = { ids: string[]; status: string; reason?: string };

// =============================================================================
// Mutation option factories
//
// Each factory returns a `mutationOptions()` payload. The hook wires it into
// `useMutation`. Mutations invalidate `partsKeys.all` via symbol reference —
// the namespace lives in one place; renaming flows everywhere.
//
// `meta` tags fire global error/success toasts via the QueryClient's
// MutationCache (see src/lib/queryClient.ts). Per-call onError/onSuccess can
// still be supplied at the useMutation call site and runs in addition to the
// global handlers.
// =============================================================================

export const createPartMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<CreatePartResponse, unknown, CreatePartInput>({
        mutationKey: partsMutationKeys.create,
        mutationFn: (data) =>
            api.api_Parts_create(data as never, { headers: csrfHeaders() }) as Promise<CreatePartResponse>,
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't create part", successMessage: "Part created" },
    });

/**
 * Update mutation with optimistic cache write. The user sees their edit
 * reflected immediately in the detail query; if the server rejects, the
 * cache rolls back via the `context.prev` captured in `onMutate`.
 */
export const updatePartMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<UpdatePartResponse, unknown, UpdatePartVariables, { prev?: PartsResponse }>({
        mutationKey: partsMutationKeys.update,
        mutationFn: ({ id, data }) =>
            api.api_Parts_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<UpdatePartResponse>,
        onMutate: async ({ id, data }) => {
            const detailKey = partsKeys.detail({ params: { id } });
            await queryClient.cancelQueries({ queryKey: detailKey });
            const prev = queryClient.getQueryData<PartsResponse>(detailKey);
            if (prev) {
                queryClient.setQueryData<PartsResponse>(detailKey, { ...prev, ...data } as PartsResponse);
            }
            return { prev };
        },
        onError: (_err, { id }, ctx) => {
            if (ctx?.prev) {
                queryClient.setQueryData(partsKeys.detail({ params: { id } }), ctx.prev);
            }
        },
        onSettled: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't update part", successMessage: "Part updated" },
    });

export const partIncrementMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: partsMutationKeys.increment,
        mutationFn: (id) =>
            api.api_Parts_increment_create(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't increment part", successMessage: "Part incremented" },
    });

export const bulkIncrementPartsMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<Awaited<ReturnType<typeof api.api_Parts_bulk_increment_create>>, unknown, string[]>({
        mutationKey: partsMutationKeys.bulkIncrement,
        mutationFn: (ids) =>
            api.api_Parts_bulk_increment_create({ ids }, { headers: csrfHeaders() }),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't increment parts", successMessage: "Parts incremented" },
    });

export const bulkRollbackPartsMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<Awaited<ReturnType<typeof api.api_Parts_bulk_rollback_create>>, unknown, string[]>({
        mutationKey: partsMutationKeys.bulkRollback,
        mutationFn: (ids) =>
            api.api_Parts_bulk_rollback_create({ ids }, { headers: csrfHeaders() }),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't roll back parts", successMessage: "Parts rolled back" },
    });

export const bulkSetStatusPartsMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<Awaited<ReturnType<typeof api.api_Parts_bulk_set_status_create>>, unknown, BulkSetStatusVariables>({
        mutationKey: partsMutationKeys.bulkSetStatus,
        mutationFn: (payload) =>
            api.api_Parts_bulk_set_status_create(
                { ids: payload.ids, status: payload.status as never, reason: payload.reason },
                { headers: csrfHeaders() },
            ),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't update part status", successMessage: "Part status updated" },
    });

// =============================================================================
// Mutation hooks — thin wrappers over the factories.
// =============================================================================

export const useCreatePart = () => {
    const queryClient = useQueryClient();
    return useMutation(createPartMutationOptions(queryClient));
};

export const useUpdatePart = () => {
    const queryClient = useQueryClient();
    return useMutation(updatePartMutationOptions(queryClient));
};

export function usePartIncrementMutation() {
    const queryClient = useQueryClient();
    return useMutation(partIncrementMutationOptions(queryClient));
}

export const useBulkIncrementParts = () => {
    const queryClient = useQueryClient();
    return useMutation(bulkIncrementPartsMutationOptions(queryClient));
};

export const useBulkRollbackParts = () => {
    const queryClient = useQueryClient();
    return useMutation(bulkRollbackPartsMutationOptions(queryClient));
};

export const useBulkSetStatusParts = () => {
    const queryClient = useQueryClient();
    return useMutation(bulkSetStatusPartsMutationOptions(queryClient));
};

// -----------------------------------------------------------------------------
// Lot-cohesion engine — split + privileged advance
// -----------------------------------------------------------------------------

export const splitPartFromLotMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, SplitFromLotVariables>({
        mutationKey: partsMutationKeys.splitFromLot,
        mutationFn: ({ id, reason, rework_target_step_id, notes }) =>
            api.api_Parts_split_from_lot_create(
                {
                    reason,
                    ...(rework_target_step_id ? { rework_target_step_id } : {}),
                    ...(notes ? { notes } : {}),
                } as never,
                { params: { id }, headers: csrfHeaders() },
            ),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: { errorMessage: "Couldn't split part from lot", successMessage: "Part split from lot" },
    });

export const useSplitPartFromLot = () => {
    const queryClient = useQueryClient();
    return useMutation(splitPartFromLotMutationOptions(queryClient));
};

export const advanceLotMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, AdvanceLotVariables>({
        mutationKey: partsMutationKeys.advanceLot,
        mutationFn: ({ work_order_id, step_id }) =>
            api.api_Parts_advance_lot_create(
                { work_order_id, step_id } as never,
                { headers: csrfHeaders() },
            ),
        onSuccess: () => invalidateAllParts(queryClient),
        meta: {
            errorMessage: "Couldn't advance lot",
            successMessage: "Lot advancement evaluated",
        },
    });

export const useAdvanceLot = () => {
    const queryClient = useQueryClient();
    return useMutation(advanceLotMutationOptions(queryClient));
};

type AdvanceLotResult = {
    status: string;
    reason?: string;
    parts_advanced?: string[];
    blockers_by_part?: Record<string, string[]>;
    split_parts_advanced?: string[];
    split_parts_blocked?: Record<string, string[]>;
};

/**
 * Operator "Complete step" — the canonical advancement trigger.
 *
 * Calls `POST /api/Parts/{id}/complete_step/` which synchronously runs
 * the gate via `try_advance_lot` and returns the result. The operator
 * sees the outcome (advanced N steps / blocked with reasons) inline.
 */
export const completeStepMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<AdvanceLotResult, unknown, string>({
        mutationKey: partsMutationKeys.completeStep,
        mutationFn: (partId) =>
            api.api_Parts_complete_step_create(undefined as never, {
                params: { id: partId },
                headers: csrfHeaders(),
            }) as Promise<AdvanceLotResult>,
        onSuccess: () => invalidateAllParts(queryClient),
        meta: {
            errorMessage: "Couldn't complete step",
            // Per-call onSuccess handler surfaces the structured result;
            // the global meta toast just confirms the request landed.
            successMessage: "Step submitted",
        },
    });

export const useCompleteStep = () => {
    const queryClient = useQueryClient();
    return useMutation(completeStepMutationOptions(queryClient));
};

// =============================================================================
// 4a — decision-point resolution
// =============================================================================

export type DecisionBranch = { step_id: string; step_name: string } | null;
export type DecisionOptions = {
    is_decision_point: boolean;
    decision_type?: string;
    default_branch?: DecisionBranch;
    alternate_branch?: DecisionBranch;
    qa_suggested?: string | null;
};

/** Decision-point metadata for a part's current step (4a). Drives the
 *  runtime resolver: branch labels for MANUAL, auto-route note for QA_RESULT. */
export function useDecisionOptions(partId: string | null | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        queryKey: [...partsKeys.detail(partId ?? ""), "decision_options"] as const,
        queryFn: () =>
            api.api_Parts_decision_options_retrieve({
                params: { id: String(partId) },
            }) as Promise<DecisionOptions>,
        enabled: Boolean(partId) && (options?.enabled ?? true),
    });
}

/** Resolve a MANUAL decision point by choosing the routing branch (4a).
 *  Manager/lead-gated server-side (`resolve_step_decision`). */
export type ResolveDecisionResult = {
    result: string;
    new_step_id: string | null;
    new_step_name: string | null;
    part_status: string;
};
export const useResolveDecision = () => {
    const queryClient = useQueryClient();
    return useMutation<ResolveDecisionResult, unknown, { partId: string; decision: "DEFAULT" | "ALTERNATE" }>({
        mutationFn: ({ partId, decision }) =>
            api.api_Parts_resolve_decision_create(
                { decision } as never,
                { params: { id: partId }, headers: { "X-CSRFToken": getCookie("csrftoken") } },
            ) as Promise<ResolveDecisionResult>,
        onSuccess: () => invalidateAllParts(queryClient),
    });
};

// =============================================================================
// 4b — rework-cycle / escalation status
// =============================================================================

export type ReworkStatus = {
    total_rework_count: number;
    current_step_name: string | null;
    max_visits: number | null;
    current_visits: number;
    remaining: number | null;
    at_limit: boolean;
    escalation_step_name: string | null;
};

/** Rework-cycle status for a part: cumulative reworks, visits vs the current
 *  step's cap, and the escalation target when the cap is exceeded (4b). */
export function useReworkStatus(partId: string | null | undefined, options?: { enabled?: boolean }) {
    return useQuery({
        queryKey: [...partsKeys.detail(partId ?? ""), "rework_status"] as const,
        queryFn: () =>
            api.api_Parts_rework_status_retrieve({
                params: { id: String(partId) },
            }) as Promise<ReworkStatus>,
        enabled: Boolean(partId) && (options?.enabled ?? true),
    });
}
