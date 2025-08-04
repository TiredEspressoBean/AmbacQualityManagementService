import {useRetrieveProcesses} from "@/hooks/useRetrieveProcesses";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditProcessActionsCell} from "@/components/edit-process-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useProcessList({
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

    return useRetrieveProcesses({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    })
}

export function ProcessEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Process"
            modelName="Processes"
            showDetailsLink={true}
            useList={useProcessList}
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
                { header: "Updated At", renderCell: (p: any) => new Date(p.updated_at).toLocaleString() },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString() },
                { header: "Number of Steps", renderCell: (p: any) => p.num_steps },
                { header: "Reman Process", renderCell: (p: any) => p.is_remanufactured ? "Yes" : "No" },
                { header: "Version", renderCell: (p: any) => p.version || "-" }, // depending on serialization
            ]}
            renderActions={(process) => <EditProcessActionsCell processId={process.id} />}
            onCreate={() => navigate({ to: "/ProcessForm/create" })}
        />
    );
}
