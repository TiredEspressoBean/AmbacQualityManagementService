import { useNavigate } from "@tanstack/react-router";
import { useTrainingRecords } from "@/hooks/useTrainingRecords";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { EditTrainingRecordActionCell } from "@/components/edit-training-record-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";

function useTrainingRecordsList({
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
    return useTrainingRecords({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function TrainingRecordsPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Training Records"
            modelName="TrainingRecord"
            useList={useTrainingRecordsList}
            sortOptions={[
                { label: "Completed (Newest)", value: "-completed_date" },
                { label: "Completed (Oldest)", value: "completed_date" },
                { label: "Expires (Soonest)", value: "expires_date" },
                { label: "Expires (Latest)", value: "-expires_date" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
            ]}
            columns={[
                {
                    header: "Trainee",
                    renderCell: (record: any) =>
                        record.user_info?.full_name || record.user_info?.username || "—",
                },
                {
                    header: "Training Type",
                    renderCell: (record: any) =>
                        record.training_type_info?.name || "—",
                },
                {
                    header: "Status",
                    renderCell: (record: any) => {
                        const status = record.status?.toUpperCase() || 'CURRENT';
                        return <StatusBadge status={status} />;
                    },
                },
                {
                    header: "Completed",
                    renderCell: (record: any) =>
                        record.completed_date
                            ? new Date(record.completed_date).toLocaleDateString()
                            : "—",
                },
                {
                    header: "Expires",
                    renderCell: (record: any) => {
                        if (!record.expires_date) return <span className="text-muted-foreground">Never</span>;
                        const isExpired = record.status === 'expired';
                        return (
                            <span className={isExpired ? "text-destructive font-medium" : ""}>
                                {new Date(record.expires_date).toLocaleDateString()}
                            </span>
                        );
                    },
                },
                {
                    header: "Trainer",
                    renderCell: (record: any) =>
                        record.trainer_info?.full_name || record.trainer_info?.username || <span className="text-muted-foreground">—</span>,
                },
            ]}
            renderActions={(record) => <EditTrainingRecordActionCell recordId={record.id} />}
            onCreate={() => navigate({ to: "/TrainingRecordForm/new" })}
            showDetailsLink={false}
        />
    );
}
