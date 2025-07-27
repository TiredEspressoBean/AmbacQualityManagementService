import {useRetrieveDocuments} from "@/hooks/useRetrieveDocuments";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditDocumentsActionsCell} from "@/components/edit-documents-action-cell.tsx";

// Custom wrapper hook for consistent usage
function useDocumentsList({
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

    return useRetrieveDocuments({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    })
}

export function DocumentsEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Documents"
            useList={useDocumentsList}
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
                { header: "File Name", renderCell: (p: any) => p.file_name },
                { header: "ID prefix", renderCell: (p: any) => p.ID_prefix },
                { header: "Version", renderCell: (p: any) => p.version || "-" }, // depending on serialization
                { header: "Uploaded At", renderCell: (p: any) => new Date(p.upload_date).toLocaleString() },
                { header: "Uploaded By", renderCell: (p: any) => p.uploaded_by_name },
                { header: "Version", renderCell: (p: any) => p.version || "-" },
            ]}
            renderActions={(document) => <EditDocumentsActionsCell documentId={document.id} />}
            onCreate={() => navigate({ to: "/DocumentsForm/create" })}
        />
    );
}