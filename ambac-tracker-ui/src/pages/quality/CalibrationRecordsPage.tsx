import { useNavigate } from "@tanstack/react-router";
import { useCalibrationRecords } from "@/hooks/useCalibrationRecords";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { EditCalibrationRecordActionCell } from "@/components/edit-calibration-record-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";

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
    return useCalibrationRecords({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
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
                {
                    header: "Equipment",
                    renderCell: (record: any) => (
                        <div>
                            <div className="font-medium">{record.equipment_info?.name || "—"}</div>
                            {record.equipment_info?.equipment_type && (
                                <div className="text-xs text-muted-foreground">
                                    {record.equipment_info.equipment_type}
                                </div>
                            )}
                        </div>
                    ),
                },
                {
                    header: "Result",
                    renderCell: (record: any) => (
                        <StatusBadge
                            status={record.result?.toUpperCase() || 'PASS'}
                            label={record.result_display}
                        />
                    ),
                },
                {
                    header: "Status",
                    renderCell: (record: any) => {
                        const status = record.status?.toUpperCase() || 'CURRENT';
                        return <StatusBadge status={status} />;
                    },
                },
                {
                    header: "Calibration Date",
                    renderCell: (record: any) =>
                        record.calibration_date
                            ? new Date(record.calibration_date).toLocaleDateString()
                            : "—",
                },
                {
                    header: "Due Date",
                    renderCell: (record: any) => {
                        if (!record.due_date) return <span className="text-muted-foreground">—</span>;
                        const isOverdue = record.status === 'overdue';
                        return (
                            <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                {new Date(record.due_date).toLocaleDateString()}
                                {isOverdue && " (Overdue)"}
                            </span>
                        );
                    },
                },
                {
                    header: "Type",
                    renderCell: (record: any) => record.calibration_type_display || record.calibration_type || "—",
                },
                {
                    header: "Certificate #",
                    renderCell: (record: any) =>
                        record.certificate_number || <span className="text-muted-foreground">—</span>,
                },
            ]}
            renderActions={(record) => <EditCalibrationRecordActionCell recordId={record.id} />}
            onCreate={() => navigate({ to: "/CalibrationRecordForm/new" })}
            showDetailsLink={false}
        />
    );
}
