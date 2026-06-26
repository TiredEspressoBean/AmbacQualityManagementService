import { useQuery, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

export type PartTypeQualitySummary = {
    parts_total: number;
    reports: {
        total: number;
        passed: number;
        failed: number;
        pending: number;
        fpy: number | null;
    };
    open: { dispositions: number; capas: number };
    defect_pareto: { error_type: string; count: number }[];
    spc: {
        measurement_id: string;
        label: string;
        unit: string;
        n: number;
        in_spec_pct: number;
        mean: number;
        ppk: number | null;
        capable: boolean | null;
    }[];
    recent_failures: {
        id: string;
        report_number: string;
        created_at: string;
        part: string | null;
        step: string | null;
    }[];
    fpy_trend: { date: string; label: string; fpy: number | null; total: number }[];
};

export const partTypeQualitySummaryOptions = (id?: string) =>
    queryOptions({
        queryKey: ["partTypeQualitySummary", id] as const,
        queryFn: () =>
            api.api_PartTypes_quality_summary_retrieve({
                params: { id: id! },
            }) as Promise<PartTypeQualitySummary>,
    });

export function usePartTypeQualitySummary(id?: string) {
    return useQuery({
        ...partTypeQualitySummaryOptions(id),
        enabled: !!id,
    });
}
