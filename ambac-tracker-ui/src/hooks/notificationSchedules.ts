/**
 * Notification schedules API — consolidated hooks for all three scopes.
 *
 * Mirrors `notificationRules.ts`. Three endpoints, three Schema types, one
 * cache namespace. Mutations invalidate via `notificationSchedulesKeys.all`.
 *
 * Tenant + customer schedules are admin-managed (require
 * `edit_notification_rules` server-side). Personal schedules are
 * self-managed by the owner via `/profile/notifications`.
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

export type TenantSchedule = Schema<"TenantSchedule">;
export type CustomerSchedule = Schema<"CustomerSchedule">;
export type PersonalSchedule = Schema<"PersonalSchedule">;

export type TenantScheduleRequest = Schema<"TenantScheduleRequest">;
export type CustomerScheduleRequest = Schema<"CustomerScheduleRequest">;
export type PersonalScheduleRequest = Schema<"PersonalScheduleRequest">;

export type PatchedTenantScheduleRequest = Schema<"PatchedTenantScheduleRequest">;
export type PatchedCustomerScheduleRequest = Schema<"PatchedCustomerScheduleRequest">;
export type PatchedPersonalScheduleRequest = Schema<"PatchedPersonalScheduleRequest">;

type PaginatedTenantScheduleList = Schema<"PaginatedTenantScheduleList">;
type PaginatedCustomerScheduleList = Schema<"PaginatedCustomerScheduleList">;
type PaginatedPersonalScheduleList = Schema<"PaginatedPersonalScheduleList">;

export type ScheduledContentProviderCatalogEntry = Schema<"ScheduledContentProviderCatalog">;

export interface SchedulesListFilters {
    search?: string;
    ordering?: string;
    limit?: number;
    offset?: number;
}

export interface CustomerSchedulesListFilters extends SchedulesListFilters {
    customer?: string;
}

// =============================================================================
// Cache keys
// =============================================================================

export const notificationSchedulesKeys = {
    all: ["notificationSchedules"] as const,
    scope: (scope: "tenant" | "customer" | "personal") =>
        ["notificationSchedules", scope] as const,
    list: (
        scope: "tenant" | "customer" | "personal",
        filters: SchedulesListFilters = {},
    ) => ["notificationSchedules", scope, "list", filters] as const,
    detail: (scope: "tenant" | "customer" | "personal", id: string) =>
        ["notificationSchedules", scope, "detail", id] as const,
    providers: () => ["notificationSchedules", "providers"] as const,
};

// =============================================================================
// Query option factories
// =============================================================================

export const tenantSchedulesOptions = (filters: SchedulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.list("tenant", filters),
        queryFn: () =>
            api.api_notifications_schedules_tenant_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                },
            } as never) as Promise<PaginatedTenantScheduleList>,
    });

export const retrieveTenantScheduleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.detail("tenant", id),
        queryFn: () =>
            api.api_notifications_schedules_tenant_retrieve({
                params: { id },
            }) as Promise<TenantSchedule>,
    });

export const customerSchedulesOptions = (filters: CustomerSchedulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.list("customer", filters),
        queryFn: () =>
            api.api_notifications_schedules_customer_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                    customer: filters.customer,
                },
            } as never) as Promise<PaginatedCustomerScheduleList>,
    });

export const retrieveCustomerScheduleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.detail("customer", id),
        queryFn: () =>
            api.api_notifications_schedules_customer_retrieve({
                params: { id },
            }) as Promise<CustomerSchedule>,
    });

export const personalSchedulesOptions = (filters: SchedulesListFilters = {}) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.list("personal", filters),
        queryFn: () =>
            api.api_notifications_schedules_personal_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                },
            } as never) as Promise<PaginatedPersonalScheduleList>,
    });

export const retrievePersonalScheduleOptions = (id: string) =>
    queryOptions({
        queryKey: notificationSchedulesKeys.detail("personal", id),
        queryFn: () =>
            api.api_notifications_schedules_personal_retrieve({
                params: { id },
            }) as Promise<PersonalSchedule>,
    });

export const scheduledContentProvidersOptions = () =>
    queryOptions({
        queryKey: notificationSchedulesKeys.providers(),
        queryFn: () =>
            api.api_notifications_schedules_providers_list() as Promise<
                ScheduledContentProviderCatalogEntry[]
            >,
    });

// =============================================================================
// Read hooks
// =============================================================================

export const useTenantSchedules = (
    filters: SchedulesListFilters = {},
    options?: Omit<ReturnType<typeof tenantSchedulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...tenantSchedulesOptions(filters), ...options });

export const useCustomerSchedules = (
    filters: CustomerSchedulesListFilters = {},
    options?: Omit<ReturnType<typeof customerSchedulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...customerSchedulesOptions(filters), ...options });

export const usePersonalSchedules = (
    filters: SchedulesListFilters = {},
    options?: Omit<ReturnType<typeof personalSchedulesOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...personalSchedulesOptions(filters), ...options });

export const useRetrieveTenantSchedule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrieveTenantScheduleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useRetrieveCustomerSchedule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrieveCustomerScheduleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useRetrievePersonalSchedule = (id: string, options?: { enabled?: boolean }) =>
    useQuery({ ...retrievePersonalScheduleOptions(id), enabled: (options?.enabled ?? true) && !!id });

export const useScheduledContentProviders = () =>
    useQuery(scheduledContentProvidersOptions());

// =============================================================================
// Mutations
// =============================================================================

export const notificationSchedulesMutationKeys = {
    createTenant: ["notificationSchedules", "tenant", "create"] as const,
    updateTenant: ["notificationSchedules", "tenant", "update"] as const,
    deleteTenant: ["notificationSchedules", "tenant", "delete"] as const,
    createCustomer: ["notificationSchedules", "customer", "create"] as const,
    updateCustomer: ["notificationSchedules", "customer", "update"] as const,
    deleteCustomer: ["notificationSchedules", "customer", "delete"] as const,
    createPersonal: ["notificationSchedules", "personal", "create"] as const,
    updatePersonal: ["notificationSchedules", "personal", "update"] as const,
    deletePersonal: ["notificationSchedules", "personal", "delete"] as const,
};

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

const invalidateAllSchedules = (queryClient: QueryClient) =>
    queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] === notificationSchedulesKeys.all[0],
    });

type UpdateVariables<TPatch> = { id: string; data: TPatch };

/**
 * Optimistic list-cache patch for one schedule by id. Mirrors the
 * notificationRules.ts pattern: snapshot every cached list under the
 * scope, apply the patch in-place, return the snapshot for rollback.
 */
async function optimisticListPatch<TRow extends { id: string }>(
    queryClient: QueryClient,
    scope: "tenant" | "customer" | "personal",
    id: string,
    patch: Record<string, unknown>,
): Promise<Array<[readonly unknown[], { results?: TRow[] } | undefined]>> {
    const filter = { queryKey: notificationSchedulesKeys.scope(scope) };
    await queryClient.cancelQueries(filter);
    const prev = queryClient.getQueriesData<{ results?: TRow[] }>(filter);
    queryClient.setQueriesData<{ results?: TRow[] }>(filter, (old) => {
        if (!old || !old.results) return old;
        return {
            ...old,
            results: old.results.map((r) =>
                r.id === id ? ({ ...r, ...patch } as TRow) : r,
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

// ---- Tenant -----------------------------------------------------------

export const createTenantScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<TenantSchedule, unknown, TenantScheduleRequest>({
        mutationKey: notificationSchedulesMutationKeys.createTenant,
        mutationFn: (data) =>
            api.api_notifications_schedules_tenant_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<TenantSchedule>,
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't create schedule", successMessage: "Schedule created" },
    });

export const updateTenantScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<TenantSchedule, unknown, UpdateVariables<PatchedTenantScheduleRequest>, OptimisticCtx>({
        mutationKey: notificationSchedulesMutationKeys.updateTenant,
        mutationFn: ({ id, data }) =>
            api.api_notifications_schedules_tenant_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<TenantSchedule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<TenantSchedule>(queryClient, "tenant", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't update schedule", successMessage: "Schedule saved" },
    });

export const deleteTenantScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationSchedulesMutationKeys.deleteTenant,
        mutationFn: (id) =>
            api.api_notifications_schedules_tenant_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't delete schedule", successMessage: "Schedule deleted" },
    });

// ---- Customer ---------------------------------------------------------

export const createCustomerScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<CustomerSchedule, unknown, CustomerScheduleRequest>({
        mutationKey: notificationSchedulesMutationKeys.createCustomer,
        mutationFn: (data) =>
            api.api_notifications_schedules_customer_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<CustomerSchedule>,
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't create schedule", successMessage: "Schedule created" },
    });

export const updateCustomerScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<CustomerSchedule, unknown, UpdateVariables<PatchedCustomerScheduleRequest>, OptimisticCtx>({
        mutationKey: notificationSchedulesMutationKeys.updateCustomer,
        mutationFn: ({ id, data }) =>
            api.api_notifications_schedules_customer_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<CustomerSchedule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<CustomerSchedule>(queryClient, "customer", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't update schedule", successMessage: "Schedule saved" },
    });

export const deleteCustomerScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationSchedulesMutationKeys.deleteCustomer,
        mutationFn: (id) =>
            api.api_notifications_schedules_customer_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't delete schedule", successMessage: "Schedule deleted" },
    });

// ---- Personal ---------------------------------------------------------

export const createPersonalScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<PersonalSchedule, unknown, PersonalScheduleRequest>({
        mutationKey: notificationSchedulesMutationKeys.createPersonal,
        mutationFn: (data) =>
            api.api_notifications_schedules_personal_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<PersonalSchedule>,
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't create schedule", successMessage: "Subscription created" },
    });

export const updatePersonalScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<PersonalSchedule, unknown, UpdateVariables<PatchedPersonalScheduleRequest>, OptimisticCtx>({
        mutationKey: notificationSchedulesMutationKeys.updatePersonal,
        mutationFn: ({ id, data }) =>
            api.api_notifications_schedules_personal_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<PersonalSchedule>,
        onMutate: async ({ id, data }) => ({
            prev: await optimisticListPatch<PersonalSchedule>(queryClient, "personal", id, data),
        }),
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) rollbackListPatch(queryClient, ctx.prev);
        },
        onSettled: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't update schedule", successMessage: "Subscription saved" },
    });

export const deletePersonalScheduleMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: notificationSchedulesMutationKeys.deletePersonal,
        mutationFn: (id) =>
            api.api_notifications_schedules_personal_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAllSchedules(queryClient),
        meta: { errorMessage: "Couldn't delete schedule", successMessage: "Subscription deleted" },
    });

// =============================================================================
// Mutation hooks
// =============================================================================

export const useCreateTenantSchedule = () => {
    const qc = useQueryClient();
    return useMutation(createTenantScheduleMutationOptions(qc));
};
export const useUpdateTenantSchedule = () => {
    const qc = useQueryClient();
    return useMutation(updateTenantScheduleMutationOptions(qc));
};
export const useDeleteTenantSchedule = () => {
    const qc = useQueryClient();
    return useMutation(deleteTenantScheduleMutationOptions(qc));
};

export const useCreateCustomerSchedule = () => {
    const qc = useQueryClient();
    return useMutation(createCustomerScheduleMutationOptions(qc));
};
export const useUpdateCustomerSchedule = () => {
    const qc = useQueryClient();
    return useMutation(updateCustomerScheduleMutationOptions(qc));
};
export const useDeleteCustomerSchedule = () => {
    const qc = useQueryClient();
    return useMutation(deleteCustomerScheduleMutationOptions(qc));
};

export const useCreatePersonalSchedule = () => {
    const qc = useQueryClient();
    return useMutation(createPersonalScheduleMutationOptions(qc));
};
export const useUpdatePersonalSchedule = () => {
    const qc = useQueryClient();
    return useMutation(updatePersonalScheduleMutationOptions(qc));
};
export const useDeletePersonalSchedule = () => {
    const qc = useQueryClient();
    return useMutation(deletePersonalScheduleMutationOptions(qc));
};
