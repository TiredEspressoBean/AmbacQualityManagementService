import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";
import type { MeasurementDefinitionSPC } from "./useSpcHierarchy";

export type SpcDataPoint = {
    id: string;
    value: number;
    timestamp: string;
    report_id: string;
    part_erp_id: string;
    operator_name: string | null;
    is_within_spec: boolean;
};

export type SpcStatistics = {
    count: number;
    mean: number | null;
    std_dev: number | null;
    min: number | null;
    max: number | null;
    within_spec_count: number;
    out_of_spec_count: number;
};

export type SpcDataResponse = {
    definition: MeasurementDefinitionSPC;
    process_name: string;
    step_name: string;
    data_points: SpcDataPoint[];
    statistics: SpcStatistics;
};

type UseSpcDataParams = {
    measurementId: string | null;
    days?: number;
    limit?: number;
    enabled?: boolean;
};

export const useSpcData = ({
    measurementId,
    days = 90,
    limit = 500,
    enabled = true,
}: UseSpcDataParams) => {
    return useQuery<SpcDataResponse>({
        queryKey: ["spc-data", measurementId, days, limit],
        queryFn: () => api.api_spc_data_retrieve({
            queries: {
                measurement_id: measurementId!,
                days,
                limit
            }
        }) as Promise<SpcDataResponse>,
        enabled: enabled && measurementId !== null,
    });
};
