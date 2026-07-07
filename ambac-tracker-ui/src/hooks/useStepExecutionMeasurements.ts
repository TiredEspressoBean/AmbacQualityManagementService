import { useQuery, queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type TypeEnum } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";

// Types for required measurements response
export type RequiredMeasurementsResponse = {
    step_execution_id: string;
    step_name: string;
    definitions: Array<{
        id: string;
        label: string;
        type: TypeEnum;
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

// Extract queries type from the Zodios endpoint's config param. Indexing is
// used (not a conditional `extends { queries?: infer Q }`) because the param is
// optional — the conditional distributes over `| undefined` and collapses back
// to the whole config object, which broke callers passing bare query objects.
type StepExecutionMeasurementsListQueries = NonNullable<
    Parameters<typeof api.api_StepExecutionMeasurements_list>[0]
>["queries"];

// Optional config for advanced cases (headers, etc.)
type ListHookConfig = {
    headers?: Record<string, string>;
};

/**
 * Factory for listing step execution measurements
 */
export const stepExecutionMeasurementsOptions = (queries?: StepExecutionMeasurementsListQueries, config?: ListHookConfig) => queryOptions({
    queryKey: ["step-execution-measurements", queries, config] as const,
    queryFn: () => api.api_StepExecutionMeasurements_list(
        (queries || config ? { queries, ...config } : undefined) as never,
    ),
});

/**
 * Query hook for listing step execution measurements
 */
export function useStepExecutionMeasurements(
    queries?: StepExecutionMeasurementsListQueries,
    config?: ListHookConfig,
    options?: Omit<ReturnType<typeof stepExecutionMeasurementsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...stepExecutionMeasurementsOptions(queries, config),
        ...options
    });
}

/**
 * Factory for getting required measurements for a step execution
 */
export const requiredMeasurementsOptions = (stepExecutionId: string | undefined) => queryOptions({
    queryKey: ["required-measurements", stepExecutionId] as const,
    queryFn: () => api.api_StepExecutionMeasurements_required_retrieve({
        queries: {
            step_execution: stepExecutionId!
        }
    }) as Promise<RequiredMeasurementsResponse>,
});

/**
 * Query hook for getting required measurements for a step execution
 */
export function useRequiredMeasurements(
    stepExecutionId: string | undefined,
    options?: Omit<ReturnType<typeof requiredMeasurementsOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...requiredMeasurementsOptions(stepExecutionId),
        enabled: !!stepExecutionId,
        ...options
    });
}

/**
 * Factory for checking measurement compliance
 */
export const measurementComplianceOptions = (stepExecutionId: string | undefined) => queryOptions({
    queryKey: ["measurement-compliance", stepExecutionId] as const,
    queryFn: () => api.api_StepExecutionMeasurements_check_compliance_retrieve({
        queries: {
            step_execution: stepExecutionId!
        }
    }) as Promise<ComplianceCheckResponse>,
});

/**
 * Query hook for checking measurement compliance
 */
export function useMeasurementCompliance(
    stepExecutionId: string | undefined,
    options?: Omit<ReturnType<typeof measurementComplianceOptions>, "queryKey" | "queryFn">
) {
    return useQuery({
        ...measurementComplianceOptions(stepExecutionId),
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
        }) => api.api_StepExecutionMeasurements_create(data as never, {
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
