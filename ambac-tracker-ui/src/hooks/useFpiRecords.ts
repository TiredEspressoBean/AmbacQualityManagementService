import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Types for FPI status check response
export type FpiCheckStatusResponse = {
    requires_fpi: boolean;
    satisfied: boolean;
    has_pending: boolean;
    pending_fpi_id: string | null;
    message: string;
};

// Types for FPI get-or-create response
export type FpiGetOrCreateResponse = {
    created: boolean;
    fpi: any;
};

/**
 * Query hook for listing FPI records
 */
export function useFpiRecords(
    queries?: Parameters<typeof api.api_FPIRecords_list>[0],
    options?: Omit<UseQueryOptions<any, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["fpi-records", queries],
        queryFn: () => api.api_FPIRecords_list(queries),
        ...options
    });
}

/**
 * Query hook for checking FPI status for a work order/step
 */
export function useFpiCheckStatus(
    workOrderId: string | undefined,
    stepId: string | undefined,
    options?: Omit<UseQueryOptions<FpiCheckStatusResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["fpi-status", workOrderId, stepId],
        queryFn: () => api.api_FPIRecords_check_status_retrieve({
            queries: {
                work_order: workOrderId!,
                step: stepId!
            }
        }) as Promise<FpiCheckStatusResponse>,
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
        mutationFn: (data: {
            work_order: string;
            step: string;
            equipment?: string;
            shift_date?: string;
        }) => api.api_FPIRecords_get_or_create_create(data, {
            headers: {
                "X-CSRFToken": getCookie("csrftoken") ?? "",
            },
        }) as Promise<FpiGetOrCreateResponse>,

        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: ["fpi-records"]
            });
            queryClient.invalidateQueries({
                queryKey: ["fpi-status", variables.work_order, variables.step]
            });
        },
    });
}

/**
 * Mutation hook for passing an FPI
 */
export function useFpiPass() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
            api.api_FPIRecords_pass_create({ notes }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fpi-records"] });
            queryClient.invalidateQueries({ queryKey: ["fpi-status"] });
            queryClient.invalidateQueries({ queryKey: ["parts"] });
        },
    });
}

/**
 * Mutation hook for failing an FPI
 */
export function useFpiFail() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
            api.api_FPIRecords_fail_create({ notes }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fpi-records"] });
            queryClient.invalidateQueries({ queryKey: ["fpi-status"] });
            queryClient.invalidateQueries({ queryKey: ["parts"] });
        },
    });
}

/**
 * Mutation hook for waiving an FPI
 */
export function useFpiWaive() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, reason }: { id: string; reason: string }) =>
            api.api_FPIRecords_waive_create({ reason }, {
                params: { id },
                headers: {
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
            }),

        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fpi-records"] });
            queryClient.invalidateQueries({ queryKey: ["fpi-status"] });
            queryClient.invalidateQueries({ queryKey: ["parts"] });
        },
    });
}
