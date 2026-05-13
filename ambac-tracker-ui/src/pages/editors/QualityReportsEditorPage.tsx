import { useQualityReports, qualityReportsOptions, qualityReportsMetadataOptions } from "@/hooks/useQualityReports";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditQualityReportActionsCell } from "@/components/edit-quality-report-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"QualityReports">>();

// Backend returns nested info objects typed as `{}` passthrough in the schema.
// These local interfaces reflect the actual runtime shapes until the serializers are updated.
// FLAG: QualityReports serializer should declare part_info, step_info, detected_by_info, verified_by_info fields explicitly.
interface PartInfo { erp_id?: string }
interface StepInfo { name?: string; process_name?: string }
interface UserInfo { full_name?: string; username?: string }

// Default params that match what useQualityReportsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchQualityReportsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(qualityReportsOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(qualityReportsMetadataOptions());
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
    const queries: Parameters<typeof useQualityReports>[0] = {
        offset,
        limit,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useQualityReports(queries);
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
                col({
                    header: "Report #",
                    renderCell: (qr) => (
                        <span className="font-mono text-sm text-primary">{qr.report_number || "—"}</span>
                    ),
                }),
                col({
                    header: "Status",
                    renderCell: (qr) => (
                        <StatusBadge status={qr.status} label={qr.status_display} />
                    ),
                }),
                col({
                    header: "Part",
                    renderCell: (qr) => (qr.part_info as PartInfo)?.erp_id || (qr.part ? `#${qr.part}` : "—"),
                }),
                col({
                    header: "Step",
                    renderCell: (qr) => {
                        if (!qr.step_info) return qr.step ? `#${qr.step}` : "—";
                        const info = qr.step_info as StepInfo;
                        if (info.process_name) {
                            return `${info.process_name} > ${info.name}`;
                        }
                        return info.name;
                    },
                }),
                col({
                    header: "Detected By",
                    renderCell: (qr) => {
                        const info = qr.detected_by_info as UserInfo;
                        return info?.full_name || info?.username || "—";
                    },
                }),
                col({
                    header: "Verified By",
                    renderCell: (qr) => {
                        const info = qr.verified_by_info as UserInfo;
                        return info?.full_name || info?.username || "—";
                    },
                }),
                col({
                    header: "Created",
                    renderCell: (qr) => new Date(qr.created_at).toLocaleDateString(),
                }),
            ]}
            renderActions={(qualityReport) => <EditQualityReportActionsCell qualityReportId={qualityReport.id} />}
            onCreate={() => navigate({ to: "/editor/qualityReports/create" })}
        />
    );
}
