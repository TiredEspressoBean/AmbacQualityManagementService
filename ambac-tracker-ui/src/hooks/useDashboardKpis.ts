import { api } from "@/lib/api/generated";
import { useQuery } from "@tanstack/react-query";

export type DashboardKpis = {
    active_capas: number;
    open_ncrs: number;
    overdue_capas: number;
    parts_in_quarantine: number;
    current_fpy: number;
};

export const useDashboardKpis = () => {
    return useQuery<DashboardKpis>({
        queryKey: ["dashboard-kpis"],
        queryFn: () => api.api_dashboard_kpis_retrieve() as Promise<DashboardKpis>,
        refetchInterval: 2 * 60 * 1000, // Poll every 2 minutes - actionable KPIs
    });
};
