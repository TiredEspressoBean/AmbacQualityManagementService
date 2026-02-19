import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

// ===== CAPA Status Distribution =====
export type CapaStatusDataPoint = {
    status: string;
    value: number;
};

export type CapaStatusResponse = {
    data: CapaStatusDataPoint[];
    total: number;
};

export const useCapaStatusDistribution = (enabled = true) => {
    return useQuery<CapaStatusResponse>({
        queryKey: ["capa-status-distribution"],
        queryFn: () => api.api_dashboard_capa_status_retrieve() as Promise<CapaStatusResponse>,
        enabled,
        refetchInterval: 5 * 60 * 1000, // Poll every 5 minutes
    });
};

// ===== In-Process Actions =====
export type InProcessAction = {
    id: string;
    db_id: string;
    type: string;
    title: string;
    assignee: string;
    due: string | null;
    status: string;
};

export type InProcessActionsResponse = {
    data: InProcessAction[];
};

export const useInProcessActions = (limit = 10, enabled = true) => {
    return useQuery<InProcessActionsResponse>({
        queryKey: ["in-process-actions", limit],
        queryFn: () => api.api_dashboard_in_process_actions_retrieve({ limit }) as Promise<InProcessActionsResponse>,
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable items
    });
};

// ===== Failed Inspections =====
export type FailedInspection = {
    id: string;
    part: string;
    step: string;
    error_type: string;
    inspector: string;
    date: string;
};

export type FailedInspectionsResponse = {
    data: FailedInspection[];
};

export const useFailedInspections = (limit = 10, days = 14, enabled = true) => {
    return useQuery<FailedInspectionsResponse>({
        queryKey: ["failed-inspections", limit, days],
        queryFn: () => api.api_dashboard_failed_inspections_retrieve({ limit, days }) as Promise<FailedInspectionsResponse>,
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - recent failures
    });
};

// ===== Open Dispositions =====
export type OpenDisposition = {
    id: string;
    part: string;
    disposition: string;
    reason: string;
    assignee: string;
    created: string;
    status: string;
};

export type OpenDispositionsResponse = {
    data: OpenDisposition[];
};

export const useOpenDispositions = (limit = 10, enabled = true) => {
    return useQuery<OpenDispositionsResponse>({
        queryKey: ["open-dispositions", limit],
        queryFn: () => api.api_dashboard_open_dispositions_retrieve({ limit }) as Promise<OpenDispositionsResponse>,
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable items
    });
};
