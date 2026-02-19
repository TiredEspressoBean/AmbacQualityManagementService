import { useQualityReports } from "@/hooks/useQualityReports";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditQualityReportActionsCell } from "@/components/edit-quality-report-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useQualityReportsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchQualityReportsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["quality-reports", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_ErrorReports_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "QualityReports", "ErrorReports"],
        queryFn: () => api.api_ErrorReports_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useQualityReportsList({
    offset,
    limit,
    ordering,
    search,
    filters,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    return useQualityReports({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function QualityReportsEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Quality Reports"
            modelName="QualityReports"
            showDetailsLink={true}
            useList={useQualityReportsList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Report # (A-Z)", value: "report_number" },
                { label: "Report # (Z-A)", value: "-report_number" },
                { label: "Status (A-Z)", value: "status" },
                { label: "Status (Z-A)", value: "-status" },
            ]}
            columns={[
                {
                    header: "Report #",
                    renderCell: (qr: any) => (
                        <span className="font-mono text-sm text-primary">{qr.report_number || "—"}</span>
                    ),
                },
                {
                    header: "Status",
                    renderCell: (qr: any) => (
                        <StatusBadge status={qr.status} label={qr.status_display} />
                    ),
                },
                {
                    header: "Part",
                    renderCell: (qr: any) => (qr.part_info as any)?.erp_id || (qr.part ? `#${qr.part}` : "—"),
                },
                {
                    header: "Step",
                    renderCell: (qr: any) => {
                        if (!qr.step_info) return qr.step ? `#${qr.step}` : "—";
                        if ((qr.step_info as any).process_name) {
                            return `${(qr.step_info as any).process_name} > ${(qr.step_info as any).name}`;
                        }
                        return (qr.step_info as any).name;
                    },
                },
                {
                    header: "Detected By",
                    renderCell: (qr: any) =>
                        (qr.detected_by_info as any)?.full_name || (qr.detected_by_info as any)?.username || "—",
                },
                {
                    header: "Verified By",
                    renderCell: (qr: any) =>
                        (qr.verified_by_info as any)?.full_name || (qr.verified_by_info as any)?.username || "—",
                },
                {
                    header: "Created",
                    renderCell: (qr: any) => new Date(qr.created_at).toLocaleDateString(),
                },
            ]}
            renderActions={(qualityReport) => <EditQualityReportActionsCell qualityReportId={qualityReport.id} />}
            onCreate={() => navigate({ to: "/editor/qualityReports/create" })}
        />
    );
}
