import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditPartTypeActionsCell} from "@/components/edit-part-type-action-cell.tsx";

// Custom wrapper hook for consistent usage
function usePartTypesList({
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

    return useRetrievePartTypes({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    })
}

export function PartTypesEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Part Types"
            modelName="PartTypes"
            showDetailsLink={true}
            useList={usePartTypesList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "Updated (Newest)", value: "-updated_at" },
                { label: "Updated (Oldest)", value: "updated_at" },
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "ID prefix (A-Z)", value: "ID_prefix" },
                { label: "ID prefix (Z-A)", value: "-ID_prefix" },
            ]}
            columns={[
                { header: "Name", renderCell: (p: any) => p.name },
                { header: "ID prefix", renderCell: (p: any) => p.ID_prefix },
                { header: "Version", renderCell: (p: any) => p.version || "-" }, // depending on serialization
                { header: "Updated At", renderCell: (p: any) => new Date(p.updated_at).toLocaleString() },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString() },
                { header: "Previous Version", renderCell: (p: any) => p.previous_version_name || "-" },
            ]}
            renderActions={(partType) => <EditPartTypeActionsCell partTypeId={partType.id} />}
            onCreate={() => navigate({ to: "/PartTypeForm/create" })}
        />
    );
}
