import { useNavigate } from "@tanstack/react-router";
import { useCalibrationRecords } from "@/hooks/useCalibrationRecords";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditCalibrationRecordActionCell } from "@/components/edit-calibration-record-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"CalibrationRecord">>();

function useCalibrationRecordsList({
    offset,
    limit,
    ordering,
    search,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
}) {
    const queries: Parameters<typeof useCalibrationRecords>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useCalibrationRecords(queries);
}

export function CalibrationRecordsPage() {
    const navigate = useNavigate();

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
                    renderCell: (record) => (
                        <div>
                            <div className="font-medium">{record.equipment_info?.name || "—"}</div>
                            {record.equipment_info?.equipment_type && (
                                <div className="text-xs text-muted-foreground">
                                    {record.equipment_info.equipment_type}
                                </div>
                            )}
                        </div>
                    ),
                }),
                col({
                    header: "Result",
                    renderCell: (record) => (
                        <StatusBadge
                            status={record.result?.toUpperCase() || 'PASS'}
                            label={record.result_display}
                        />
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
                            ? new Date(record.calibration_date).toLocaleDateString()
                            : "—",
                }),
                col({
                    header: "Due Date",
                    renderCell: (record) => {
                        if (!record.due_date) return <span className="text-muted-foreground">—</span>;
                        const isOverdue = record.status === 'OVERDUE';
                        return (
                            <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                {new Date(record.due_date).toLocaleDateString()}
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
            onCreate={() => navigate({ to: "/CalibrationRecordForm/new" })}
            showDetailsLink={false}
        />
    );
}
