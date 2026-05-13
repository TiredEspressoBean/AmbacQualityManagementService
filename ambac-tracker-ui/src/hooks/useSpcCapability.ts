import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";
import type { MeasurementDefinitionSPC } from "./useSpcHierarchy";

export type SpcCapabilityResponse = {
    definition: MeasurementDefinitionSPC;
    sample_size: number;
    subgroup_size?: number;
    num_subgroups?: number;
    usl?: number;
    lsl?: number;
    mean?: number;
    std_dev_within?: number;
    std_dev_overall?: number;
    cp?: number | null;
    cpk?: number | null;
    pp?: number | null;
    ppk?: number | null;
    interpretation?: string;
    error?: string;
};

type UseSpcCapabilityParams = {
    measurementId: string | null;
    days?: number;
    subgroupSize?: number;
    enabled?: boolean;
};

export const spcCapabilityOptions = (measurementId: string | null, days = 90, subgroupSize = 5) => queryOptions({
    queryKey: ["spc-capability", measurementId, days, subgroupSize] as const,
    queryFn: () => api.api_spc_capability_retrieve({
        queries: {
            measurement_id: measurementId!,
            days,
            subgroup_size: subgroupSize
        }
    }) as Promise<SpcCapabilityResponse>,
});

export const useSpcCapability = ({
    measurementId,
    days = 90,
    subgroupSize = 5,
    enabled = true,
}: UseSpcCapabilityParams) => {
    return useQuery({
        ...spcCapabilityOptions(measurementId, days, subgroupSize),
        enabled: enabled && measurementId !== null,
    });
};
