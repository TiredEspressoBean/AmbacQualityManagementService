/**
 * External contacts API — customer-side recipients for customer-scoped rules.
 *
 * Single namespace, same pattern as `notificationRules.ts` — list + retrieve
 * + create/update/delete, all invalidating `externalContactsKeys.all`.
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

export type ExternalContact = Schema<"ExternalContact">;
export type ExternalContactRequest = Schema<"ExternalContactRequest">;
export type PatchedExternalContactRequest = Schema<"PatchedExternalContactRequest">;

type PaginatedExternalContactList = Schema<"PaginatedExternalContactList">;

export interface ExternalContactsFilters {
    search?: string;
    ordering?: string;
    limit?: number;
    offset?: number;
    /** Filter to one customer's contacts. */
    customer?: string;
}

// =============================================================================
// Cache keys
// =============================================================================

export const externalContactsKeys = {
    all: ["externalContacts"] as const,
    list: (filters: ExternalContactsFilters = {}) =>
        ["externalContacts", "list", filters] as const,
    detail: (id: string) => ["externalContacts", "detail", id] as const,
};

// =============================================================================
// Query options
// =============================================================================

export const externalContactsOptions = (filters: ExternalContactsFilters = {}) =>
    queryOptions({
        queryKey: externalContactsKeys.list(filters),
        queryFn: () =>
            api.api_notifications_external_contacts_list({
                queries: {
                    search: filters.search,
                    ordering: filters.ordering,
                    limit: filters.limit,
                    offset: filters.offset,
                    customer: filters.customer,
                },
            } as never) as Promise<PaginatedExternalContactList>,
    });

export const retrieveExternalContactOptions = (id: string) =>
    queryOptions({
        queryKey: externalContactsKeys.detail(id),
        queryFn: () =>
            api.api_notifications_external_contacts_retrieve({
                params: { id },
            }) as Promise<ExternalContact>,
    });

// =============================================================================
// Read hooks
// =============================================================================

export const useExternalContacts = (
    filters: ExternalContactsFilters = {},
    options?: Omit<ReturnType<typeof externalContactsOptions>, "queryKey" | "queryFn">,
) => useQuery({ ...externalContactsOptions(filters), ...options });

export const useRetrieveExternalContact = (id: string, options?: { enabled?: boolean }) =>
    useQuery({
        ...retrieveExternalContactOptions(id),
        enabled: (options?.enabled ?? true) && !!id,
    });

// =============================================================================
// Mutations
// =============================================================================

export const externalContactsMutationKeys = {
    create: ["externalContacts", "create"] as const,
    update: ["externalContacts", "update"] as const,
    delete: ["externalContacts", "delete"] as const,
};

const csrfHeaders = () => ({ "X-CSRFToken": getCookie("csrftoken") ?? "" });

const invalidateAll = (queryClient: QueryClient) =>
    queryClient.invalidateQueries({
        predicate: (q) => q.queryKey[0] === externalContactsKeys.all[0],
    });

type UpdateVariables = { id: string; data: PatchedExternalContactRequest };

export const createExternalContactMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<ExternalContact, unknown, ExternalContactRequest>({
        mutationKey: externalContactsMutationKeys.create,
        mutationFn: (data) =>
            api.api_notifications_external_contacts_create(data as never, {
                headers: csrfHeaders(),
            }) as Promise<ExternalContact>,
        onSuccess: () => invalidateAll(queryClient),
        meta: { errorMessage: "Couldn't create contact", successMessage: "Contact created" },
    });

export const updateExternalContactMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<ExternalContact, unknown, UpdateVariables>({
        mutationKey: externalContactsMutationKeys.update,
        mutationFn: ({ id, data }) =>
            api.api_notifications_external_contacts_partial_update(data as never, {
                params: { id },
                headers: csrfHeaders(),
            }) as Promise<ExternalContact>,
        onSuccess: () => invalidateAll(queryClient),
        meta: { errorMessage: "Couldn't update contact", successMessage: "Contact saved" },
    });

export const deleteExternalContactMutationOptions = (queryClient: QueryClient) =>
    mutationOptions<unknown, unknown, string>({
        mutationKey: externalContactsMutationKeys.delete,
        mutationFn: (id) =>
            api.api_notifications_external_contacts_destroy(undefined as never, {
                params: { id },
                headers: csrfHeaders(),
            }),
        onSuccess: () => invalidateAll(queryClient),
        meta: { errorMessage: "Couldn't delete contact", successMessage: "Contact deleted" },
    });

export const useCreateExternalContact = () => {
    const queryClient = useQueryClient();
    return useMutation(createExternalContactMutationOptions(queryClient));
};

export const useUpdateExternalContact = () => {
    const queryClient = useQueryClient();
    return useMutation(updateExternalContactMutationOptions(queryClient));
};

export const useDeleteExternalContact = () => {
    const queryClient = useQueryClient();
    return useMutation(deleteExternalContactMutationOptions(queryClient));
};
