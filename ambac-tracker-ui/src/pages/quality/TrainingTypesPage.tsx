import { useNavigate } from "@tanstack/react-router";
import { useTrainingTypes } from "@/hooks/useTrainingTypes";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { EditTrainingTypeActionCell } from "@/components/edit-training-type-action-cell";

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
    return useTrainingTypes({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
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
                {
                    header: "Name",
                    renderCell: (type: any) => (
                        <span className="font-medium">{type.name}</span>
                    ),
                },
                {
                    header: "Description",
                    renderCell: (type: any) => (
                        <span className="max-w-[300px] truncate block text-muted-foreground" title={type.description}>
                            {type.description || "—"}
                        </span>
                    ),
                },
                {
                    header: "Validity Period",
                    renderCell: (type: any) => {
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
                },
            ]}
            renderActions={(type) => <EditTrainingTypeActionCell typeId={type.id} />}
            onCreate={() => navigate({ to: "/TrainingTypeForm/new" })}
            showDetailsLink={false}
        />
    );
}
