import { parseISO } from "date-fns";
import { Link, useNavigate } from "@tanstack/react-router";
import { useCalibrationRecords } from "@/hooks/useCalibrationRecords";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditCalibrationRecordActionCell } from "@/components/edit-calibration-record-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Schema } from "@/lib/api/types";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { foundUnfit } from "@/lib/calibration-exposure";

const col = createColumnHelper<Schema<"CalibrationRecord">>();

function useCalibrationRecordsList({
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
    // Filters come from the list metadata's filterset (the dropdowns ModelEditorPage
    // renders), so they are this endpoint's own query params.
    const queries: Parameters<typeof useCalibrationRecords>[0] = { ...filters, offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useCalibrationRecords(queries);
}

export function CalibrationRecordsPage() {
    const navigate = useNavigate();
    const canSeeReports = usePermissionSet().has("view_qualityreports");

    return (
        <ModelEditorPage
            title="Calibration Records"
            modelName="CalibrationRecord"
            useList={useCalibrationRecordsList}
            sortOptions={[
                { label: "Calibration Date (Newest)", value: "-calibration_date" },
                { label: "Calibration Date (Oldest)", value: "calibration_date" },
                { label: "Due Date (Soonest)", value: "due_date" },
                { label: "Due Date (Latest)", value: "-due_date" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
            ]}
            columns={[
                col({
                    header: "Equipment",
                    renderCell: (record) => {
                        const info = record.equipment_info as { name?: string; equipment_type?: string } | null | undefined;
                        return (
                            <div>
                                <div className="font-medium">{info?.name || "—"}</div>
                                {info?.equipment_type && (
                                    <div className="text-xs text-muted-foreground">
                                        {info.equipment_type}
                                    </div>
                                )}
                            </div>
                        );
                    },
                }),
                col({
                    header: "Result",
                    renderCell: (record) => (
                        <div className="space-y-1">
                            <StatusBadge
                                status={record.result?.toUpperCase() || 'PASS'}
                                label={record.result_display}
                            />
                            {canSeeReports && foundUnfit(record) && (
                                <Link
                                    to="/quality/calibrations/records/$id/exposure"
                                    params={{ id: record.id }}
                                    className="block text-xs text-primary hover:underline"
                                >
                                    What it measured
                                </Link>
                            )}
                        </div>
                    ),
                }),
                col({
                    header: "Status",
                    renderCell: (record) => {
                        const status = record.status?.toUpperCase() || 'CURRENT';
                        return <StatusBadge status={status} />;
                    },
                }),
                col({
                    header: "Calibration Date",
                    renderCell: (record) =>
                        record.calibration_date
                            ? parseISO(record.calibration_date).toLocaleDateString()
                            : "—",
                }),
                col({
                    header: "Due Date",
                    renderCell: (record) => {
                        if (!record.due_date) return <span className="text-muted-foreground">—</span>;
                        const isOverdue = record.status === 'OVERDUE';
                        return (
                            <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                {parseISO(record.due_date).toLocaleDateString()}
                                {isOverdue && " (Overdue)"}
                            </span>
                        );
                    },
                }),
                col({
                    header: "Type",
                    renderCell: (record) => record.calibration_type_display || record.calibration_type || "—",
                }),
                col({
                    header: "Certificate #",
                    renderCell: (record) =>
                        record.certificate_number || <span className="text-muted-foreground">—</span>,
                }),
            ]}
            renderActions={(record) => <EditCalibrationRecordActionCell recordId={record.id} />}
            onCreate={() => navigate({ to: "/quality/calibrations/records/new" })}
            showDetailsLink={false}
            listQueryKey={["calibration-records"]}
        />
    );
}
