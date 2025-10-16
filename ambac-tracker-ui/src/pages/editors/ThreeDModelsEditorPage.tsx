import { useRetrieveThreeDModels } from "@/hooks/useRetrieveThreeDModels.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditThreeDModelActionsCell } from "@/components/edit-three-d-model-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useThreeDModelsList({
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
    return useRetrieveThreeDModels({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function ThreeDModelsEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="3D Models"
            modelName="ThreeDModels"
            useList={useThreeDModelsList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Uploaded (Newest)", value: "-uploaded_at" },
                { label: "Uploaded (Oldest)", value: "uploaded_at" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Updated (Newest)", value: "-updated_at" },
                { label: "Updated (Oldest)", value: "updated_at" },
            ]}
            columns={[
                { header: "Name", renderCell: (model: any) => model.name },
                { header: "Part Type", renderCell: (model: any) => model.part_type_display || "N/A" },
                { header: "Step", renderCell: (model: any) => model.step_display || "N/A" },
                { header: "File Type", renderCell: (model: any) => model.file_type || "N/A" },
            ]}
            renderActions={(model) => <EditThreeDModelActionsCell modelId={model.id} />}
            onCreate={() => navigate({ to: "/ThreeDModelsForm/create" })}
        />
    );
}
