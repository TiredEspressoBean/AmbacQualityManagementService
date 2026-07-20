import { useNavigate } from "@tanstack/react-router";
import { useTrainingRecords } from "@/hooks/useTrainingRecords";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditTrainingRecordActionCell } from "@/components/edit-training-record-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import type { Schema } from "@/lib/api/types";

const LEVEL_SHORT: Record<number, string> = {
    1: "Trainee",
    2: "Assisted",
    3: "Qualified",
    4: "Expert",
};

const col = createColumnHelper<Schema<"TrainingRecord">>();

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
    const queries: Parameters<typeof useTrainingRecords>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useTrainingRecords(queries);
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
                { label: "Level (Highest)", value: "-level" },
                { label: "Level (Lowest)", value: "level" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
            ]}
            columns={[
                col({
                    header: "Trainee",
                    renderCell: (record) => {
                        const info = record.user_info as { full_name?: string; username?: string } | null | undefined;
                        return info?.full_name || info?.username || "—";
                    },
                }),
                col({
                    header: "Training Type",
                    renderCell: (record) => {
                        const info = record.training_type_info as { name?: string } | null | undefined;
                        return info?.name || "—";
                    },
                }),
                col({
                    header: "Level",
                    renderCell: (record) => {
                        const lvl = record.level ?? 3;
                        return (
                            <Badge variant="outline" title={record.level_display ?? undefined}>
                                L{lvl} {LEVEL_SHORT[lvl] ?? ""}
                            </Badge>
                        );
                    },
                }),
                col({
                    header: "Status",
                    renderCell: (record) => {
                        const status = record.status?.toUpperCase() || 'CURRENT';
                        return <StatusBadge status={status} />;
                    },
                }),
                col({
                    header: "Completed",
                    renderCell: (record) =>
                        record.completed_date
                            ? new Date(record.completed_date).toLocaleDateString()
                            : "—",
                }),
                col({
                    header: "Expires",
                    renderCell: (record) => {
                        if (!record.expires_date) return <span className="text-muted-foreground">Never</span>;
                        const isExpired = record.status === 'EXPIRED';
                        return (
                            <span className={isExpired ? "text-destructive font-medium" : ""}>
                                {new Date(record.expires_date).toLocaleDateString()}
                            </span>
                        );
                    },
                }),
                col({
                    header: "Trainer",
                    renderCell: (record) => {
                        const info = record.trainer_info as { full_name?: string; username?: string } | null | undefined;
                        return info?.full_name || info?.username || <span className="text-muted-foreground">—</span>;
                    },
                }),
            ]}
            renderActions={(record) => <EditTrainingRecordActionCell recordId={record.id} />}
            onCreate={() => navigate({ to: "/TrainingRecordForm/$id", params: { id: "new" } })}
            showDetailsLink={false}
        />
    );
}
