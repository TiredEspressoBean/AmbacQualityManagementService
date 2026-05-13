import { useState } from "react";
import { useRetrieveDocuments, documentsOptions, documentsMetadataOptions } from "@/hooks/useRetrieveDocuments";
import { useNavigate, Link } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditDocumentsActionsCell } from "@/components/edit-documents-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { FileSignature } from "lucide-react";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Documents">>();

// Default params that match what useDocumentsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchDocumentsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(documentsOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(documentsMetadataOptions());
};

// Custom wrapper hook with filter support
function useDocumentsListWithFilter(needsMyApproval: boolean) {
    return function useDocumentsList({
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
         
        return useRetrieveDocuments(
            // eslint-disable-next-line local/no-as-any -- `needs_my_approval` is a backend-only filter not declared in the OpenAPI spec
            {
                offset,
                limit,
                ordering,
                search,
                needs_my_approval: needsMyApproval ? true : undefined,
                ...filters,
            } as any,
        );
    };
}

export function DocumentsEditorPage() {
    const navigate = useNavigate();
    const [needsMyApproval, setNeedsMyApproval] = useState(false);

    const filterToolbar = (
        <Button
            variant={needsMyApproval ? "default" : "outline"}
            size="sm"
            onClick={() => setNeedsMyApproval(!needsMyApproval)}
            className="gap-2"
        >
            <FileSignature className="h-4 w-4" />
            Needs My Approval
        </Button>
    );

    return (
        <ModelEditorPage
            title="Documents"
            modelName="Documents"
            useList={useDocumentsListWithFilter(needsMyApproval)}
            extraToolbarContent={filterToolbar}
            columns={[
                col({
                    header: "File Name",
                    renderCell: (doc) => (
                        <Link
                            to="/documents/$id"
                            params={{ id: String(doc.id) }}
                            className="text-primary hover:underline font-medium"
                        >
                            {doc.file_name}
                        </Link>
                    ),
                    priority: 1,
                }),
                col({
                    header: "ID",
                    renderCell: (doc) => (
                        <span className="font-mono text-sm">{doc.id}</span>
                    ),
                    priority: 1,
                }),
                col({
                    header: "Version",
                    renderCell: (doc) => (
                        <span className="font-mono">v{doc.version || 1}</span>
                    ),
                    priority: 2,
                }),
                col({
                    header: "Status",
                    renderCell: (doc) => (
                        <StatusBadge status={doc.status} label={doc.status_display} />
                    ),
                    priority: 1,
                }),
                col({
                    header: "Classification",
                    renderCell: (doc) => doc.classification ? (
                        <StatusBadge status={doc.classification} />
                    ) : (
                        <span className="text-muted-foreground">—</span>
                    ),
                    priority: 2,
                }),
                col({
                    header: "Uploaded",
                    renderCell: (doc) => (
                        <span className="text-sm">
                            {doc.upload_date
                                ? new Date(doc.upload_date).toLocaleDateString()
                                : "—"}
                        </span>
                    ),
                    priority: 4,
                }),
                col({
                    header: "Uploaded By",
                    renderCell: (doc) => (doc.uploaded_by_info?.full_name as string | undefined) || (doc.uploaded_by_info?.email as string | undefined) || "—",
                    priority: 5,
                }),
            ]}
            renderActions={(document) => <EditDocumentsActionsCell documentId={document.id} />}
            onCreate={() => navigate({ to: "/DocumentForm/create" })}
            showDetailsLink={false}
        />
    );
}
