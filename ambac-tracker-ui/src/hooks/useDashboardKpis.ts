import { api } from "@/lib/api/generated";
import { useQuery, queryOptions } from "@tanstack/react-query";

export type DashboardKpis = {
    active_capas: number;
    open_ncrs: number;
    overdue_capas: number;
    parts_in_quarantine: number;
    /** First-pass yield with planned repairs (REPAIR results) left out of both sides. */
    current_fpy: number;
    /** Share of inspections that found planned repair work; null when there were none. */
    needed_repair_rate: number | null;
};

export const dashboardKpisOptions = () => queryOptions({
    queryKey: ["dashboard-kpis"] as const,
    queryFn: () => api.api_dashboard_kpis_retrieve() as Promise<DashboardKpis>,
});

export const useDashboardKpis = () => {
    return useQuery({
        ...dashboardKpisOptions(),
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable KPIs
    });
};
