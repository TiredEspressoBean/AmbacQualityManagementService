import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type DimensionalResult = {
    part_erp_id: string;
    step_name: string;
    step_order: number;
    measurement_label: string;
    nominal: number;
    upper_tol: number;
    lower_tol: number;
    usl: number;
    lsl: number;
    actual: number;
    deviation: number;
    unit: string;
    is_within_spec: boolean;
    timestamp: string;
    operator: string | null;
    report_id: string;
};

export type DimensionalResultsSummary = {
    total_measurements: number;
    within_spec: number;
    out_of_spec: number;
    pass_rate: number;
};

export type DimensionalResultsResponse = {
    part: {
        id: string;
        erp_id: string;
        part_type: string | null;
    } | null;
    work_order: {
        id: string;
        identifier: string;
        order_id: string;
    } | null;
    results: DimensionalResult[];
    summary: DimensionalResultsSummary;
};

type UseDimensionalResultsParams = {
    partId?: string | null;
    workOrderId?: string | null;
    enabled?: boolean;
};

export const dimensionalResultsOptions = (partId?: string | null, workOrderId?: string | null) => queryOptions({
    queryKey: ["dimensional-results", partId, workOrderId] as const,
    queryFn: async () => {
        if (partId === null && workOrderId === null) {
            throw new Error("Either partId or workOrderId is required");
        }
        return api.api_spc_dimensional_results_retrieve({
            queries: {
                part_id: partId ?? undefined,
                work_order_id: workOrderId ?? undefined,
            }
        }) as Promise<DimensionalResultsResponse>;
    },
});

export const useDimensionalResults = ({
    partId,
    workOrderId,
    enabled = true,
}: UseDimensionalResultsParams) => {
    return useQuery({
        ...dimensionalResultsOptions(partId, workOrderId),
        enabled: enabled && (partId !== null || workOrderId !== null),
    });
};
