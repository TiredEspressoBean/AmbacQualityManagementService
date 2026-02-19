import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

// Types matching the backend response
export type MeasurementDefinitionSPC = {
    id: string;
    label: string;
    type: string;
    unit: string;
    nominal: number | null;
    upper_tol: number | null;
    lower_tol: number | null;
};

export type StepSPC = {
    id: string;
    name: string;
    order: number;
    measurements: MeasurementDefinitionSPC[];
};

export type ProcessSPC = {
    id: string;
    name: string;
    part_type_name: string;
    steps: StepSPC[];
};

export const useSpcHierarchy = () => {
    return useQuery<ProcessSPC[]>({
        queryKey: ["spc-hierarchy"],
        queryFn: () => api.api_spc_hierarchy_list() as Promise<ProcessSPC[]>,
    });
};
