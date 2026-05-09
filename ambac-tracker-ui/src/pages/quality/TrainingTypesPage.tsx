import { useNavigate } from "@tanstack/react-router";
import { useTrainingTypes } from "@/hooks/useTrainingTypes";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditTrainingTypeActionCell } from "@/components/edit-training-type-action-cell";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"TrainingType">>();

function useTrainingTypesList({
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
    const queries: Parameters<typeof useTrainingTypes>[0] = { offset, limit };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useTrainingTypes(queries);
}

export function TrainingTypesPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Training Types"
            modelName="TrainingType"
            useList={useTrainingTypesList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Validity Period (Shortest)", value: "validity_period_days" },
                { label: "Validity Period (Longest)", value: "-validity_period_days" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
            ]}
            columns={[
                col({
                    header: "Name",
                    renderCell: (type) => (
                        <span className="font-medium">{type.name}</span>
                    ),
                }),
                col({
                    header: "Description",
                    renderCell: (type) => (
                        <span className="max-w-[300px] truncate block text-muted-foreground" title={type.description}>
                            {type.description || "—"}
                        </span>
                    ),
                }),
                col({
                    header: "Validity Period",
                    renderCell: (type) => {
                        if (!type.validity_period_days) {
                            return <span className="text-muted-foreground">Never expires</span>;
                        }
                        const years = Math.floor(type.validity_period_days / 365);
                        const months = Math.floor((type.validity_period_days % 365) / 30);
                        const days = type.validity_period_days % 30;

                        const parts = [];
                        if (years > 0) parts.push(`${years}y`);
                        if (months > 0) parts.push(`${months}m`);
                        if (days > 0 || parts.length === 0) parts.push(`${days}d`);

                        return <span>{parts.join(' ')}</span>;
                    },
                }),
            ]}
            renderActions={(type) => <EditTrainingTypeActionCell typeId={type.id} />}
            onCreate={() => navigate({ to: "/TrainingTypeForm/$id", params: { id: "new" } })}
            showDetailsLink={false}
        />
    );
}
