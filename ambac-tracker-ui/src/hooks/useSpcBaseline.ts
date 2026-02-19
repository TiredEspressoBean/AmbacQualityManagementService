import { api, schemas } from "@/lib/api/generated";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

// Re-export generated types for convenience
export type SpcBaseline = z.infer<typeof schemas.SPCBaseline>;
export type SpcBaselineList = z.infer<typeof schemas.SPCBaselineList>;
export type SpcBaselineFreezeRequest = z.infer<typeof schemas.SPCBaselineFreezeRequest>;
export type ChartType = NonNullable<SpcBaselineFreezeRequest["chart_type"]>;
export type BaselineStatus = NonNullable<SpcBaseline["status"]>;

// Control limits structure returned by backend's control_limits property
export type ControlLimitsResponse = {
    // X-bar chart limits (camelCase from backend)
    xBarUCL?: number | null;
    xBarLCL?: number | null;
    xBarCL?: number | null;
    rangeUCL?: number | null;
    rangeLCL?: number | null;
    rangeCL?: number | null;
    // I-MR chart limits
    individualUCL?: number | null;
    individualLCL?: number | null;
    individualCL?: number | null;
    mrUCL?: number | null;
    mrCL?: number | null;
};

// Extended type with properly typed control_limits
export type SpcBaselineWithLimits = Omit<SpcBaseline, 'control_limits'> & {
    control_limits: ControlLimitsResponse;
};

/**
 * Fetch the active baseline for a measurement definition.
 * Returns null if no active baseline exists.
 */
export const useSpcActiveBaseline = (measurementId: string | null) => {
    return useQuery<SpcBaselineWithLimits | null>({
        queryKey: ["spc-baseline-active", measurementId],
        queryFn: async () => {
            try {
                const response = await api.api_spc_baselines_active_retrieve({
                    queries: { measurement_id: measurementId! }
                });
                // Cast to our properly typed version
                return (response as SpcBaselineWithLimits) || null;
            } catch (error: unknown) {
                // 404 means no active baseline - return null
                if (error && typeof error === 'object' && 'response' in error) {
                    const axiosError = error as { response?: { status?: number } };
                    if (axiosError.response?.status === 404) {
                        return null;
                    }
                }
                throw error;
            }
        },
        enabled: measurementId !== null,
    });
};

/**
 * Freeze control limits as a new baseline.
 * Automatically supersedes any existing active baseline for the same measurement.
 */
export const useFreezeSpcBaseline = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: SpcBaselineFreezeRequest) => {
            const response = await api.api_spc_baselines_freeze_create({
                body: data,
            });
            return response;
        },
        onSuccess: (newBaseline) => {
            // Invalidate the active baseline query for this measurement
            queryClient.invalidateQueries({
                queryKey: ["spc-baseline-active", newBaseline.measurement_definition],
            });
            // Also invalidate the list of all baselines
            queryClient.invalidateQueries({
                queryKey: ["spc-baselines"],
            });
        },
    });
};

/**
 * Supersede (unfreeze) a baseline.
 * This marks the baseline as superseded but keeps it in the audit trail.
 */
export const useSupersedeSpcBaseline = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ id, reason }: { id: string; reason?: string }) => {
            const response = await api.api_spc_baselines_supersede_create(
                { id },
                { body: { reason } },
            );
            return response;
        },
        onSuccess: (supersededBaseline) => {
            // Invalidate the active baseline query for this measurement
            queryClient.invalidateQueries({
                queryKey: ["spc-baseline-active", supersededBaseline.measurement_definition],
            });
            // Also invalidate the list of all baselines
            queryClient.invalidateQueries({
                queryKey: ["spc-baselines"],
            });
        },
    });
};

/**
 * Helper to convert frontend ControlLimits to API request format
 */
export const toFreezeRequest = (
    measurementId: string,
    chartType: ChartType,
    subgroupSize: number,
    limits: {
        xBarUCL?: number;
        xBarLCL?: number;
        xBarCL?: number;
        rangeUCL?: number;
        rangeLCL?: number;
        rangeCL?: number;
        individualUCL?: number;
        individualLCL?: number;
        individualCL?: number;
        mrUCL?: number;
        mrCL?: number;
    },
    sampleCount?: number,
    notes?: string
): SpcBaselineFreezeRequest => {
    const toDecimalString = (val: number | undefined) =>
        val !== undefined ? val.toFixed(6) : undefined;

    return {
        measurement_definition_id: measurementId,
        chart_type: chartType,
        subgroup_size: subgroupSize,
        // X-bar limits
        xbar_ucl: toDecimalString(limits.xBarUCL),
        xbar_cl: toDecimalString(limits.xBarCL),
        xbar_lcl: toDecimalString(limits.xBarLCL),
        range_ucl: toDecimalString(limits.rangeUCL),
        range_cl: toDecimalString(limits.rangeCL),
        range_lcl: toDecimalString(limits.rangeLCL),
        // I-MR limits
        individual_ucl: toDecimalString(limits.individualUCL),
        individual_cl: toDecimalString(limits.individualCL),
        individual_lcl: toDecimalString(limits.individualLCL),
        mr_ucl: toDecimalString(limits.mrUCL),
        mr_cl: toDecimalString(limits.mrCL),
        // Metadata
        sample_count: sampleCount,
        notes: notes,
    };
};
