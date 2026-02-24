import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Types for required measurements response
export type RequiredMeasurementsResponse = {
    step_execution_id: string;
    step_name: string;
    definitions: Array<{
        id: string;
        label: string;
        type: "NUMERIC" | "PASS_FAIL";
        unit: string;
        nominal: number | null;
        upper_tol: number | null;
        lower_tol: number | null;
        required: boolean;
        is_recorded: boolean;
    }>;
    total_required: number;
    total_recorded: number;
    missing_required: string[];
    all_required_recorded: boolean;
};

// Types for compliance check response
export type ComplianceCheckResponse = {
    step_execution_id: string;
    total_measurements: number;
    within_spec: number;
    out_of_spec: number;
    not_applicable: number;
    all_pass: boolean;
    out_of_spec_details: Array<{
        id: string;
        label: string;
        value: number | string;
        nominal: number | null;
    }>;
};

// Types for bulk record response
export type BulkRecordResponse = {
    created_count: number;
    error_count: number;
    measurements: any[];
    errors: Array<{ index: number; error: string }> | null;
};

/**
 * Query hook for listing step execution measurements
 */
export function useStepExecutionMeasurements(
    queries?: Parameters<typeof api.api_StepExecutionMeasurements_list>[0],
    options?: Omit<UseQueryOptions<any, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["step-execution-measurements", queries],
        queryFn: () => api.api_StepExecutionMeasurements_list(queries),
        ...options
    });
}

/**
 * Query hook for getting required measurements for a step execution
 */
export function useRequiredMeasurements(
    stepExecutionId: string | undefined,
    options?: Omit<UseQueryOptions<RequiredMeasurementsResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["required-measurements", stepExecutionId],
        queryFn: () => api.api_StepExecutionMeasurements_required_retrieve({
            queries: {
                step_execution: stepExecutionId!
            }
        }) as Promise<RequiredMeasurementsResponse>,
        enabled: !!stepExecutionId,
        ...options
    });
}

/**
 * Query hook for checking measurement compliance
 */
export function useMeasurementCompliance(
    stepExecutionId: string | undefined,
    options?: Omit<UseQueryOptions<ComplianceCheckResponse, Error>, "queryKey" | "queryFn">
) {
    return useQuery({
        queryKey: ["measurement-compliance", stepExecutionId],
        queryFn: () => api.api_StepExecutionMeasurements_check_compliance_retrieve({
            queries: {
                step_execution: stepExecutionId!
            }
        }) as Promise<ComplianceCheckResponse>,
        enabled: !!stepExecutionId,
        ...options
    });
}

/**
 * Mutation hook for recording a single measurement
 */
export function useRecordMeasurement() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: {
            step_execution: string;
            measurement_definition: string;
            value?: number | string;
            string_value?: string;
            equipment?: string;
        }) => api.api_StepExecutionMeasurements_create(data, {
            headers: {
                "X-CSRFToken": getCookie("csrftoken") ?? "",
            },
        }),

        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: ["step-execution-measurements"]
            });
            queryClient.invalidateQueries({
                queryKey: ["required-measurements", variables.step_execution]
            });
            queryClient.invalidateQueries({
                queryKey: ["measurement-compliance", variables.step_execution]
            });
        },
    });
}

/**
 * Mutation hook for recording multiple measurements at once
 */
export function useBulkRecordMeasurements() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: {
            step_execution: string;
            measurements: Array<{
                measurement_definition: string;
                value?: number;
                string_value?: string;
                equipment?: string;
            }>;
        }) => api.api_StepExecutionMeasurements_bulk_record_create(data, {
            headers: {
                "X-CSRFToken": getCookie("csrftoken") ?? "",
            },
        }) as Promise<BulkRecordResponse>,

        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: ["step-execution-measurements"]
            });
            queryClient.invalidateQueries({
                queryKey: ["required-measurements", variables.step_execution]
            });
            queryClient.invalidateQueries({
                queryKey: ["measurement-compliance", variables.step_execution]
            });
            queryClient.invalidateQueries({
                queryKey: ["parts"]
            });
        },
    });
}
