import { useQuery, queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Types for FPI status check response
export type FpiCheckStatusResponse = {
    requires_fpi: boolean;
    satisfied: boolean;
    /** The pass a buy-off authority may void if it was given in error (not a waive). */
    passed_fpi_id?: string | null;
    has_pending: boolean;
    pending_fpi_id: string | null;
    /** The part the buy-off is made against (first to enter the step). */
    designated_part_id: string | null;
    designated_part_label: string | null;
    /** Designated first piece has completed the step's inspection — buy-off possible. */
    first_piece_ready: boolean;
    /** Whether the current user holds sign_off_fpi (may pass/fail/waive). */
    can_sign_off: boolean;
    /** How the step's author asked a QA release to be signed: "NONE" (under the
     *  signer's login) or "PASSWORD" (they re-enter their own). The buy-off IS
     *  this step's QA release, so it meets the same bar. */
    assurance?: string;
    /** The step's scope, and who this first piece is for under it ("" per work
     *  order): "the 28 Oct shift", or the machine's name. */
    scope?: string;
    context_label?: string;
    /** False on a Per Equipment step when the part's machine isn't recorded. */
    context_known?: boolean;
    equipment_id?: string | null;
    /** The standing waiver, when the newest record is one; `can_restart` says this
     *  user may correct it by starting a new first piece. */
    waived_fpi_id?: string | null;
    can_restart?: boolean;
    message: string;
};

// Types for FPI get-or-create response
export type FpiGetOrCreateResponse = {
    created: boolean;
    fpi: any;
};

// Extract the queries bag from the Zodios endpoint. The previous conditional
// never matched -- the parameter is wrapped in DeepReadonly, so it fell
// through to the false branch and this alias was the whole `{queries}` object
// rather than the queries themselves.
type FpiRecordsListQueries = NonNullable<
    NonNullable<Parameters<typeof api.api_FPIRecords_list>[0]>["queries"]
>;

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
    headers?: Record<string, string>;
};

export const fpiRecordsOptions = (queries?: FpiRecordsListQueries, config?: ListHookConfig) => queryOptions({
    queryKey: ["fpi-records", queries, config] as const,
    queryFn: () =>
        api.api_FPIRecords_list(queries || config ? { queries, ...config } : undefined),
});

/**
 * Query hook for listing FPI records
 */
export function useFpiRecords(
    queries?: FpiRecordsListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof fpiRecordsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...fpiRecordsOptions(queries, config),
        ...options
    });
}

// `partId` answers for that part's context under the step's scope (its machine, for
// Per Equipment). The key keeps workOrderId/stepId first, so invalidating by those
// two still reaches every part's entry.
export const fpiCheckStatusOptions = (workOrderId: string | undefined, stepId: string | undefined,
                                      partId?: string) => queryOptions({
    queryKey: ["fpi-status", workOrderId, stepId, partId ?? null] as const,
    queryFn: () => api.api_FPIRecords_check_status_retrieve({
        queries: {
            work_order: workOrderId!,
            step: stepId!,
            ...(partId ? { part: partId } : {}),
        }
    }) as Promise<FpiCheckStatusResponse>,
});

/**
 * Query hook for checking FPI status for a work order/step
 */
export function useFpiCheckStatus(
    workOrderId: string | undefined,
    stepId: string | undefined,
    options?: Omit<ReturnType<typeof fpiCheckStatusOptions>, "queryKey" | "queryFn">,
    partId?: string,
) {
    return useQuery({
        ...fpiCheckStatusOptions(workOrderId, stepId, partId),
        enabled: !!workOrderId && !!stepId,
        ...options
    });
}

/**
 * Mutation hook for getting or creating an FPI record
 */
export function useFpiGetOrCreate() {
    const queryClient = useQueryClient();

    return useMutation({
        // Every caller shows the server's reason itself.
        meta: { suppressGlobalError: true },
        mutationFn: (data: {
            work_order: string;
            step: string;
            /** The part starting it: its machine is the context on a Per Equipment step. */
            part?: string;
            equipment?: string;
            shift_date?: string;
        }) => api.api_FPIRecords_get_or_create_create(data, {
            headers: {
                "X-CSRFToken": getCookie("csrftoken") ?? "",
            },
        }) as Promise<FpiGetOrCreateResponse>,

        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-records" });
            queryClient.invalidateQueries({ queryKey: ["fpi-status", variables.work_order, variables.step] });
        },
    });
}

/**
 * Mutation hook for passing an FPI
 */
export function useFpiPass() {
    const queryClient = useQueryClient();

    return useMutation({
        // Every caller shows the server's reason itself.
        meta: { suppressGlobalError: true },
        /** `cosign_*` are for the second-person path: when the caller lacks
         *  `sign_off_fpi`, an authorized QA person authenticates inline and the
         *  verdict is attributed to *them*. Omit both for a normal sign-off. */
        mutationFn: ({ id, notes, password, cosign_email, cosign_password, cosign_signature }: {
            id: string;
            notes?: string;
            /** The signer's OWN password, when the step is authored to need one and
             *  they are signing from their own session. The co-sign path proves
             *  identity with `cosign_password` instead and isn't asked twice. */
            password?: string;
            cosign_email?: string;
            cosign_password?: string;
            /** The co-signer's drawn signature (data URL), stored once they verify. */
            cosign_signature?: string;
        }) =>
            api.api_FPIRecords_pass_create({ notes, password, cosign_email, cosign_password, cosign_signature }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-records" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-status" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "parts" });
        },
    });
}

/**
 * Mutation hook for failing an FPI
 */
export function useFpiFail() {
    const queryClient = useQueryClient();

    return useMutation({
        // Every caller shows the server's reason itself.
        meta: { suppressGlobalError: true },
        /** `cosign_*`: the second-person path, as for pass. */
        mutationFn: ({ id, notes, cosign_email, cosign_password, cosign_signature }: {
            id: string; notes?: string;
            cosign_email?: string; cosign_password?: string; cosign_signature?: string;
        }) =>
            api.api_FPIRecords_fail_create({ notes, cosign_email, cosign_password, cosign_signature }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-records" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-status" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "parts" });
        },
    });
}

/**
 * Void a pass given in error: the pass is kept and marked, a fresh pending FPI holds
 * the run until the piece is re-inspected.
 */
export function useFpiVoidPass() {
    const queryClient = useQueryClient();
    return useMutation({
        meta: { suppressGlobalError: true },
        mutationFn: ({ id, reason }: { id: string; reason: string }) =>
            api.api_FPIRecords_void_pass_create({ reason }, {
                params: { id },
                headers: { "X-CSRFToken": getCookie("csrftoken") ?? "" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-records" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-status" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "parts" });
        },
    });
}

/**
 * Mutation hook for waiving an FPI
 */
export function useFpiWaive() {
    const queryClient = useQueryClient();

    return useMutation({
        // Every caller shows the server's reason itself.
        meta: { suppressGlobalError: true },
        /** A waive releases the step as surely as a pass, so it meets the same bar:
         *  the signer's own `password` when the step is authored to need one, or the
         *  `cosign_*` second-person path. */
        mutationFn: ({ id, reason, password, cosign_email, cosign_password, cosign_signature }: {
            id: string; reason: string; password?: string;
            cosign_email?: string; cosign_password?: string; cosign_signature?: string;
        }) =>
            api.api_FPIRecords_waive_create({ reason, password, cosign_email, cosign_password, cosign_signature }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-records" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "fpi-status" });
            queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] === "parts" });
        },
    });
}
