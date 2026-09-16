import { useQuery, queryOptions } from "@tanstack/react-query";
import { api, type TypeEnum } from "@/lib/api/generated";

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
        (queries || config ? { queries, ...config } : undefined),
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

/* The two write hooks that lived here -- useRecordMeasurement and
 * useBulkRecordMeasurements -- were removed. Neither had a call site, and
 * wiring either one would have been wrong: they POST straight at
 * /api/StepExecutionMeasurements/, bypassing
 * services.qms.inline_capture.record_dwi_measurement, which is what actually
 * owns this write. That service does the Tier 1 / Tier 2 split in a
 * transaction -- always a StepExecutionMeasurement, plus a QualityReports row
 * and MeasurementResult when the substep is an inspection point -- and fires
 * the quality-report side effects. Measurements captured around it would be
 * process data with no inspection record behind them.
 *
 * Real capture goes through the operator runtime: submit_substep ->
 * record_dwi_measurement. If a new surface needs to record measurements, route
 * it there rather than reinstating these.
 *
 * The read hooks above (required / compliance) are plain GETs and carry no
 * such risk, so they stay. */
