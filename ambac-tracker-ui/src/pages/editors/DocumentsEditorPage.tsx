import { Combobox } from "@/components/ui/combobox";
import { useState } from "react";
import { useRetrieveDocuments, documentsOptions, documentsMetadataOptions } from "@/hooks/useRetrieveDocuments";
import { useRetrieveDocumentTypes } from "@/hooks/useRetrieveDocumentTypes";
import { useNavigate, Link } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditDocumentsActionsCell } from "@/components/edit-documents-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { FileSignature, X } from "lucide-react";
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
function useDocumentsListWithFilter(needsMyApproval: boolean, documentTypeId: string | null) {
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
                ...(documentTypeId ? { document_type: documentTypeId } : {}),
                ...filters,
            },
        );
    };
}

export function DocumentsEditorPage() {
    const navigate = useNavigate();
    const [needsMyApproval, setNeedsMyApproval] = useState(false);
    const [documentTypeId, setDocumentTypeId] = useState<string | null>(null);
    const [docTypeSearch, setDocTypeSearch] = useState("");

    const { data: documentTypesData } = useRetrieveDocumentTypes({ search: docTypeSearch });
    const documentTypes = (documentTypesData?.results ?? []) as Array<{
        id: string;
        name: string;
        code: string;
    }>;

    const filterToolbar = (
        <div className="flex flex-wrap items-center gap-2">
            <Button
                variant={needsMyApproval ? "default" : "outline"}
                size="sm"
                onClick={() => setNeedsMyApproval(!needsMyApproval)}
                className="gap-2"
            >
                <FileSignature className="h-4 w-4" />
                Needs My Approval
            </Button>
            <Combobox
                variant={documentTypeId ? "default" : "outline"}
                size="sm"
                className="w-auto gap-2"
                contentClassName="w-72"
                value={documentTypeId}
                onChange={setDocumentTypeId}
                options={documentTypes.map((dt) => ({ value: dt.id, label: `${dt.name} (${dt.code})` }))}
                onSearch={setDocTypeSearch}
                clearLabel="All document types"
                placeholder="All document types"
                searchPlaceholder="Search document types…"
                emptyText="No document types found."
            />
            {documentTypeId && (
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDocumentTypeId(null)}
                    aria-label="Clear document type filter"
                    className="h-8 w-8 p-0"
                >
                    <X className="h-4 w-4" />
                </Button>
            )}
        </div>
    );

    return (
        <ModelEditorPage
            title="Documents"
            modelName="Documents"
            useList={useDocumentsListWithFilter(needsMyApproval, documentTypeId)}
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
                    header: "Type",
                    renderCell: (doc) => {
                        const info = doc.document_type_info as { name?: string; code?: string } | null | undefined;
                        if (info?.name) {
                            return (
                                <span className="text-sm">
                                    {info.name}
                                    {info.code && (
                                        <span className="ml-1 text-muted-foreground">({info.code})</span>
                                    )}
                                </span>
                            );
                        }
                        return <span className="text-muted-foreground">—</span>;
                    },
                    priority: 2,
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
