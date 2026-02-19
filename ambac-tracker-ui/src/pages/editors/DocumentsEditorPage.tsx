import { useState } from "react";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { useNavigate, Link } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { EditDocumentsActionsCell } from "@/components/edit-documents-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { FileSignature } from "lucide-react";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useDocumentsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchDocumentsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["document", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Documents_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Documents", "Documents"],
        queryFn: () => api.api_Documents_metadata_retrieve(),
    });
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
                {
                    header: "File Name",
                    renderCell: (doc: any) => (
                        <Link
                            to="/documents/$id"
                            params={{ id: String(doc.id) }}
                            className="text-primary hover:underline font-medium"
                        >
                            {doc.file_name}
                        </Link>
                    ),
                    priority: 1,
                },
                {
                    header: "ID",
                    renderCell: (doc: any) => (
                        <span className="font-mono text-sm">{doc.id}</span>
                    ),
                    priority: 1,
                },
                {
                    header: "Version",
                    renderCell: (doc: any) => (
                        <span className="font-mono">v{doc.version || 1}</span>
                    ),
                    priority: 2,
                },
                {
                    header: "Status",
                    renderCell: (doc: any) => (
                        <StatusBadge status={doc.status} label={doc.status_display} />
                    ),
                    priority: 1,
                },
                {
                    header: "Classification",
                    renderCell: (doc: any) => doc.classification ? (
                        <StatusBadge status={doc.classification} />
                    ) : (
                        <span className="text-muted-foreground">—</span>
                    ),
                    priority: 2,
                },
                {
                    header: "Uploaded",
                    renderCell: (doc: any) => (
                        <span className="text-sm">
                            {doc.upload_date
                                ? new Date(doc.upload_date).toLocaleDateString()
                                : "—"}
                        </span>
                    ),
                    priority: 4,
                },
                {
                    header: "Uploaded By",
                    renderCell: (doc: any) => doc.uploaded_by_info?.full_name || doc.uploaded_by_info?.email || "—",
                    priority: 5,
                },
            ]}
            renderActions={(document) => <EditDocumentsActionsCell documentId={document.id} />}
            onCreate={() => navigate({ to: "/DocumentForm/create" })}
            showDetailsLink={false}
        />
    );
}
