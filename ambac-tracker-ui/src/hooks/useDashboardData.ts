import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

// ===== CAPA Status Distribution =====
export type CapaStatusDataPoint = {
    status: string;
    value: number;
};

export type CapaStatusResponse = {
    data: CapaStatusDataPoint[];
    total: number;
};

export const capaStatusDistributionOptions = () => queryOptions({
    queryKey: ["capa-status-distribution"] as const,
    queryFn: () => api.api_dashboard_capa_status_retrieve() as Promise<CapaStatusResponse>,
});

export const useCapaStatusDistribution = (enabled = true) => {
    return useQuery({
        ...capaStatusDistributionOptions(),
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

export const inProcessActionsOptions = (limit: number) => queryOptions({
    queryKey: ["in-process-actions", limit] as const,
    queryFn: () => api.api_dashboard_in_process_actions_retrieve({ queries: { limit } }) as Promise<InProcessActionsResponse>,
});

export const useInProcessActions = (limit = 10, enabled = true) => {
    return useQuery({
        ...inProcessActionsOptions(limit),
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

export const failedInspectionsOptions = (limit: number, days: number) => queryOptions({
    queryKey: ["failed-inspections", limit, days] as const,
    queryFn: () => api.api_dashboard_failed_inspections_retrieve({ queries: { limit, days } }) as Promise<FailedInspectionsResponse>,
});

export const useFailedInspections = (limit = 10, days = 14, enabled = true) => {
    return useQuery({
        ...failedInspectionsOptions(limit, days),
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - recent failures
    });
};

// ===== Open Dispositions =====
export type OpenDisposition = {
    id: string;
    part: string;
    part_id: string | null;
    disposition: string;
    reason: string;
    assignee: string;
    created: string;
    status: string;
};

export type OpenDispositionsResponse = {
    data: OpenDisposition[];
};

export const openDispositionsOptions = (limit: number) => queryOptions({
    queryKey: ["open-dispositions", limit] as const,
    queryFn: () => api.api_dashboard_open_dispositions_retrieve({ queries: { limit } }) as Promise<OpenDispositionsResponse>,
});

export const useOpenDispositions = (limit = 10, enabled = true) => {
    return useQuery({
        ...openDispositionsOptions(limit),
        enabled,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable items
    });
};
