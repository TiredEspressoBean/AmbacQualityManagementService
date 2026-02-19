import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { useRetrieveDocumentTypes } from "@/hooks/useRetrieveDocumentTypes";
import { EditDocumentTypeActionsCell } from "@/components/edit-document-type-action-cell";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useDocumentTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchDocumentTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["document-type", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_DocumentTypes_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "DocumentTypes", "DocumentTypes"],
        queryFn: () => api.api_DocumentTypes_metadata_retrieve(),
    });
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
                { header: "Name", renderCell: (item: any) => item.name },
                { header: "Code", renderCell: (item: any) => item.code },
                {
                    header: "Requires Approval",
                    renderCell: (item: any) => (
                        <Badge variant={item.requires_approval ? "default" : "secondary"}>
                            {item.requires_approval ? "Yes" : "No"}
                        </Badge>
                    ),
                },
            ]}
            renderActions={(item) => <EditDocumentTypeActionsCell documentTypeId={item.id} />}
            onCreate={() => navigate({ to: "/DocumentTypeForm/create" })}
            showDetailsLink={false}
        />
    );
}
