import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveDocumentTypes, documentTypesOptions, documentTypesMetadataOptions } from "@/hooks/useRetrieveDocumentTypes";
import { EditDocumentTypeActionsCell } from "@/components/edit-document-type-action-cell";
import { Badge } from "@/components/ui/badge";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"DocumentType">>();

// Default params that match what useDocumentTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchDocumentTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(documentTypesOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(documentTypesMetadataOptions());
};

function useDocumentTypesList({
    offset,
    limit,
    ordering,
    search,
    filters,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveDocumentTypes({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function DocumentTypesEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Document Types"
            modelName="DocumentTypes"
            useList={useDocumentTypesList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Code (A-Z)", value: "code" },
                { label: "Code (Z-A)", value: "-code" },
            ]}
            columns={[
                col({ header: "Name", renderCell: (item) => item.name }),
                col({ header: "Code", renderCell: (item) => item.code }),
                col({
                    header: "Requires Approval",
                    renderCell: (item) => (
                        <Badge variant={item.requires_approval ? "default" : "secondary"}>
                            {item.requires_approval ? "Yes" : "No"}
                        </Badge>
                    ),
                }),
            ]}
            renderActions={(item) => <EditDocumentTypeActionsCell documentTypeId={item.id} />}
            onCreate={() => navigate({ to: "/DocumentTypeForm/create" })}
            showDetailsLink={false}
        />
    );
}
