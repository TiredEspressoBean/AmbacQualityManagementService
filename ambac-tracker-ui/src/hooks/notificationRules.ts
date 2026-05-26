/**
 * Notification rules API — consolidated hooks for all three scopes.
 *
 * Three endpoints, three Schema types, one cache namespace. Mutations
 * invalidate via `notificationRulesKeys.all` so any rule write nukes every
 * cached list — list pages don't need to know which scope changed.
 *
 * Mirrors the pattern in `parts.ts`:
 *   - `notificationRulesKeys` is the single source of truth for cache keys
 *   - Each scope gets `<scope>RulesOptions` (list) and `retrieve<Scope>RuleOptions`
 *   - Mutations follow `<verb><Scope>RuleMutationOptions(queryClient)`
 *
 * The three scopes don't share a wire shape (CustomerRule has
 * `scope_customer` + `recipient_external`, PersonalRule has `owner_user`,
 * TenantRule has only the M2M recipients), so we don't try to unify them
 * at the hook layer — callers pick the right hook for the scope they own.
 */

import {
    useQuery,
    useMutation,
    useQueryClient,
    queryOptions,
    mutationOptions,
    type QueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";
import { getCookie } from "@/lib/utils";

// =============================================================================
// Types
// =============================================================================

export type TenantRule = Schema<"TenantRule">;
export type CustomerRule = Schema<"CustomerRule">;
export type PersonalRule = Schema<"PersonalRule">;

export type TenantRuleRequest = Schema<"TenantRuleRequest">;
export type CustomerRuleRequest = Schema<"CustomerRuleRequest">;
export type PersonalRuleRequest = Schema<"PersonalRuleRequest">;

export type PatchedTenantRuleRequest = Schema<"PatchedTenantRuleRequest">;
export type PatchedCustomerRuleRequest = Schema<"PatchedCustomerRuleRequest">;
export type PatchedPersonalRuleRequest = Schema<"PatchedPersonalRuleRequest">;

type PaginatedTenantRuleList = Schema<"PaginatedTenantRuleList">;
type PaginatedCustomerRuleList = Schema<"PaginatedCustomerRuleList">;
type PaginatedPersonalRuleList = Schema<"PaginatedPersonalRuleList">;

export type NotificationEventTypeCatalogEntry = Schema<"NotificationEventTypeCatalog">;

export interface RulesListFilters {
    search?: string;
    ordering?: string;
    limit?: number;
    offset?: number;
}

export interface CustomerRulesListFilters extends RulesListFilters {
    /** Filter to one customer's rules by UUID. */
    customer?: string;
}

// =============================================================================
// Cache keys
// =============================================================================

export const notificationRulesKeys = {
    all: ["notificationRules"] as const,
    scope: (scope: "tenant" | "customer" | "personal") =>
        ["notificationRules", scope] as const,
    list: (
        scope: "tenant" | "customer" | "personal",
        filters: RulesListFilters = {},
    ) => ["notificationRules", scope, "list", filters] as const,
    detail: (scope: "tenant" | "customer" | "personal", id: string) =>
        ["notificationRules", scope, "detail", id] as const,
    events: () => ["notificationRules", "events"] as const,
};

// =============================================================================
// Query option factories — tenant scope
// =============================================================================

export const tenantRulesOptions = (filters: RulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationRulesKeys.list("tenant", filters),
        queryFn: () =>
            api.api_notifications_rules_tenant_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                },
            } as never) as Promise<PaginatedTenantRuleList>,
    });

export const retrieveTenantRuleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationRulesKeys.detail("tenant", id),
        queryFn: () =>
            api.api_notifications_rules_tenant_retrieve({
                params: { id },
            }) as Promise<TenantRule>,
    });

// =============================================================================
// Query option factories — customer scope
// =============================================================================

export const customerRulesOptions = (filters: CustomerRulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationRulesKeys.list("customer", filters),
        queryFn: () =>
            api.api_notifications_rules_customer_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                    customer: filters.customer,
                },
            } as never) as Promise<PaginatedCustomerRuleList>,
    });

export const retrieveCustomerRuleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationRulesKeys.detail("customer", id),
        queryFn: () =>
            api.api_notifications_rules_customer_retrieve({
                params: { id },
            }) as Promise<CustomerRule>,
    });

// =============================================================================
// Query option factories — personal scope
// =============================================================================

export const personalRulesOptions = (filters: RulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationRulesKeys.list("personal", filters),
        queryFn: () =>
            api.api_notifications_rules_personal_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                },
            } as never) as Promise<PaginatedPersonalRuleList>,
    });

export const retrievePersonalRuleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationRulesKeys.detail("personal", id),
        queryFn: () =>
            api.api_notifications_rules_personal_retrieve({
                params: { id },
            }) as Promise<PersonalRule>,
    });

// =============================================================================
// Event catalog (read-only)
// =============================================================================

export const notificationEventsOptions = () =>
    queryOptions({
        queryKey: notificationRulesKeys.events(),
        queryFn: () =>
            api.api_notifications_events_list() as Promise<NotificationEventTypeCatalogEntry[]>,
        // Event registry only changes on backend deploys — cache long.
        staleTime: 60 * 60 * 1000, // 1 hour
    });

// =============================================================================
// Read hooks
// =============================================================================

export const useTenantRules = (
    filters: RulesListFilters = {},
    options?: Omit<ReturnType<typeof tenantRulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...tenantRulesOptions(filters), ...options });

export const useCustomerRules = (
    filters: CustomerRulesListFilters = {},
    options?: Omit<ReturnType<typeof customerRulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...customerRulesOptions(filters), ...options });

export const usePersonalRules = (
    filters: RulesListFilters = {},
    options?: Omit<ReturnType<typeof personalRulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...personalRulesOptions(filters), ...options });

export const useRetrieveTenantRule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrieveTenantRuleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useRetrieveCustomerRule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrieveCustomerRuleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useRetrievePersonalRule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrievePersonalRuleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useNotificationEvents = () => useQuery(notificationEventsOptions());

// =============================================================================
// Mutation namespace
// =============================================================================

export const notificationRulesMutationKeys = {
    createTenant: ["notificationRules", "tenant", "create"] as const,
    updateTenant: ["notificationRules", "tenant", "update"] as const,
    deleteTenant: ["notificationRules", "tenant", "delete"] as const,
    createCustomer: ["notificationRules", "customer", "create"] as const,
    updateCustomer: ["notificationRules", "customer", "update"] as const,
    deleteCustomer: ["notificationRules", "customer", "delete"] as const,
    createPersonal: ["notificationRules", "personal", "create"] as const,
    updatePersonal: ["notificationRules", "personal", "update"] as const,
    deletePersonal: ["notificationRules", "personal", "delete"] as const,
};

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

const invalidateAllRules = (queryClient: QueryClient) =>
    queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] === notificationRulesKeys.all[0],
    });

type UpdateVariables<TPatch> = { id: string; data: TPatch };

/**
 * Apply a partial-update patch optimistically to every cached list for one
 * scope. Returns a snapshot the error handler restores from on rollback.
 *
 * Used by the three update mutations below. The detail-cache key isn't
 * touched: the next refetch (in onSettled) writes authoritative data, and
 * the editor's `useRetrieve*Rule` always runs `enabled: true` so it stays
 * fresh anyway.
 */
async function optimisticListPatch<TRule extends { id: string }>(
    queryClient: QueryClient,
    scope: "tenant" | "customer" | "personal",
    id: string,
    patch: Record<string, unknown>,
): Promise<Array<[readonly unknown[], { results?: TRule[] } | undefined]>> {
    const filter = { queryKey: notificationRulesKeys.scope(scope) };
    await queryClient.cancelQueries(filter);
    const prev = queryClient.getQueriesData<{ results?: TRule[] }>(filter);
    queryClient.setQueriesData<{ results?: TRule[] }>(filter, (old) => {
        if (!old || !old.results) return old;
        return {
            ...old,
            results: old.results.map((r) =>
                r.id === id ? ({ ...r, ...patch } as TRule) : r,
            ),
        };
    });
    return prev;
}

function rollbackListPatch(
    queryClient: QueryClient,
    snapshot: Array<[readonly unknown[], unknown]>,
): void {
    for (const [key, data] of snapshot) {
        queryClient.setQueryData(key, data);
    }
}

type OptimisticCtx = { prev: Array<[readonly unknown[], unknown]> };

// =============================================================================
// Mutation option factories — tenant
// =============================================================================

export const createTenantRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<TenantRule, unknown, TenantRuleRequest>({
        mutationKey: notificationRulesMutationKeys.createTenant,
        mutationFn: (data) =>
            api.api_notifications_rules_tenant_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<TenantRule>,
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't create rule", successMessage: "Rule created" },
    });

export const updateTenantRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<TenantRule, unknown, UpdateVariables<PatchedTenantRuleRequest>, OptimisticCtx>({
        mutationKey: notificationRulesMutationKeys.updateTenant,
        mutationFn: ({ id, data }) =>
            api.api_notifications_rules_tenant_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<TenantRule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<TenantRule>(queryClient, "tenant", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't update rule", successMessage: "Rule saved" },
    });

export const deleteTenantRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationRulesMutationKeys.deleteTenant,
        mutationFn: (id) =>
            api.api_notifications_rules_tenant_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't delete rule", successMessage: "Rule deleted" },
    });

// =============================================================================
// Mutation option factories — customer
// =============================================================================

export const createCustomerRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<CustomerRule, unknown, CustomerRuleRequest>({
        mutationKey: notificationRulesMutationKeys.createCustomer,
        mutationFn: (data) =>
            api.api_notifications_rules_customer_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<CustomerRule>,
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't create rule", successMessage: "Rule created" },
    });

export const updateCustomerRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<CustomerRule, unknown, UpdateVariables<PatchedCustomerRuleRequest>, OptimisticCtx>({
        mutationKey: notificationRulesMutationKeys.updateCustomer,
        mutationFn: ({ id, data }) =>
            api.api_notifications_rules_customer_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<CustomerRule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<CustomerRule>(queryClient, "customer", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't update rule", successMessage: "Rule saved" },
    });

export const deleteCustomerRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationRulesMutationKeys.deleteCustomer,
        mutationFn: (id) =>
            api.api_notifications_rules_customer_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't delete rule", successMessage: "Rule deleted" },
    });

// =============================================================================
// Mutation option factories — personal
// =============================================================================

export const createPersonalRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<PersonalRule, unknown, PersonalRuleRequest>({
        mutationKey: notificationRulesMutationKeys.createPersonal,
        mutationFn: (data) =>
            api.api_notifications_rules_personal_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<PersonalRule>,
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't create rule", successMessage: "Rule created" },
    });

export const updatePersonalRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<PersonalRule, unknown, UpdateVariables<PatchedPersonalRuleRequest>, OptimisticCtx>({
        mutationKey: notificationRulesMutationKeys.updatePersonal,
        mutationFn: ({ id, data }) =>
            api.api_notifications_rules_personal_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<PersonalRule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<PersonalRule>(queryClient, "personal", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't update rule", successMessage: "Rule saved" },
    });

export const deletePersonalRuleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationRulesMutationKeys.deletePersonal,
        mutationFn: (id) =>
            api.api_notifications_rules_personal_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllRules(queryClient),
        meta: { errorMessage: "Couldn't delete rule", successMessage: "Rule deleted" },
    });

// =============================================================================
// Mutation hooks
// =============================================================================

export const useCreateTenantRule = () => {
    const queryClient = useQueryClient();
    return useMutation(createTenantRuleMutationOptions(queryClient));
};

export const useUpdateTenantRule = () => {
    const queryClient = useQueryClient();
    return useMutation(updateTenantRuleMutationOptions(queryClient));
};

export const useDeleteTenantRule = () => {
    const queryClient = useQueryClient();
    return useMutation(deleteTenantRuleMutationOptions(queryClient));
};

export const useCreateCustomerRule = () => {
    const queryClient = useQueryClient();
    return useMutation(createCustomerRuleMutationOptions(queryClient));
};

export const useUpdateCustomerRule = () => {
    const queryClient = useQueryClient();
    return useMutation(updateCustomerRuleMutationOptions(queryClient));
};

export const useDeleteCustomerRule = () => {
    const queryClient = useQueryClient();
    return useMutation(deleteCustomerRuleMutationOptions(queryClient));
};

export const useCreatePersonalRule = () => {
    const queryClient = useQueryClient();
    return useMutation(createPersonalRuleMutationOptions(queryClient));
};

export const useUpdatePersonalRule = () => {
    const queryClient = useQueryClient();
    return useMutation(updatePersonalRuleMutationOptions(queryClient));
};

export const useDeletePersonalRule = () => {
    const queryClient = useQueryClient();
    return useMutation(deletePersonalRuleMutationOptions(queryClient));
};
