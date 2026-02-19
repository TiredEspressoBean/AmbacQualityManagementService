import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

export type DefectRecord = {
    id: string;
    part_erp_id: string;
    part_id: string | null;
    part_type: string;
    part_type_id: string | null;
    step: string;
    step_id: string | null;
    error_types: string[];
    inspector: string;
    date: string;
    date_formatted: string;
    order: string;
    order_id: string | null;
    work_order: string;
    work_order_id: string | null;
    disposition_status: string | null;
    disposition_type: string | null;
    description: string;
};

export type DefectRecordsFilters = {
    days?: number;
    defect_type?: string | null;
    process?: string | null;
    part_type?: string | null;
    limit?: number;
    offset?: number;
};

export type DefectRecordsResponse = {
    data: DefectRecord[];
    total: number;
    filters_applied: {
        defect_type: string | null;
        process: string | null;
        part_type: string | null;
        days: number;
    };
};

export const useDefectRecords = (filters: DefectRecordsFilters = {}, enabled = true) => {
    return useQuery<DefectRecordsResponse>({
        queryKey: ["defect-records", filters],
        queryFn: () => api.api_dashboard_defect_records_retrieve({
            days: filters.days,
            defect_type: filters.defect_type ?? undefined,
            process: filters.process ?? undefined,
            part_type: filters.part_type ?? undefined,
            limit: filters.limit,
            offset: filters.offset,
        }) as Promise<DefectRecordsResponse>,
        enabled,
        placeholderData: (previousData) => previousData,
    });
};
