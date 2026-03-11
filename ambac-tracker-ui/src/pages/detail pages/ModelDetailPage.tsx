import React, { useState, useMemo } from "react";
import {
    Card, CardHeader, CardTitle, CardContent, CardDescription,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import DocumentsSection from "@/pages/detail pages/DocumentsSection";
import AuditTrailComponent from "@/pages/detail pages/AuditTrail";
import { useNavigate } from "@tanstack/react-router";

type InfoSection = {
    title: string;
    fields: string[];
    auditLog?: boolean;
};

type RelatedModel = {
    modelType: string;
    fieldName: string; // The field that contains the related model ID
    label: string; // Display name for the relationship
    getValue?: (modelData: any) => string | number | null; // Custom getter for the related ID
};

type ActionButton = {
    label: string;
    icon?: React.ReactNode;
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
    // Function that returns the URL to navigate to, receives modelData
    getUrl: (modelData: ModelData) => string;
    // Optional condition to show/hide the button
    condition?: (modelData: ModelData) => boolean;
};

export type FieldsConfig = {
    fields: Record<string, { label: string }>;
    customRenderers?: Record<string, (value: any, modelData?: any) => React.ReactNode>;
    fetcher: (id: string) => Promise<any>;
    sections: {
        header: any[];
        info: InfoSection[];
        related: any[];
        documents: any[];
        renderer?: (modelData: any) => React.ReactNode;
    };
    // New: Define related models whose documents should be included
    relatedModels?: RelatedModel[];
    // Action buttons to display in the header
    actionButtons?: ActionButton[];
    subcomponents?: {
        RendererSidebarComponent?: React.FC<{
            modelType: string;
            modelData: any;
            documents?: Document[];
            loading?: boolean;
        }>;
        DocumentsSectionComponent?: React.FC<any>;
        AuditTrailComponent?: React.FC<any>;
    };
};

type ModelData = {
    id: string | number;
    name?: string;
    [key: string]: any;
};

type ModelDetailPageProps = {
    modelData: ModelData;
    modelType: string;
    fieldsConfig: FieldsConfig;
    RendererSidebarComponent?: FieldsConfig["subcomponents"]["RendererSidebarComponent"];
};

type DocumentWithSource = Document & {
    sourceModel?: string;
    sourceLabel?: string;
};

const ModelDetailPage: React.FC<ModelDetailPageProps> = ({
                                                             modelData,
                                                             modelType,
                                                             fieldsConfig,
                                                             RendererSidebarComponent,
                                                         }) => {
    const [selectedDocument, setSelectedDocument] = useState<DocumentWithSource | null>(null);
    const navigate = useNavigate();

    // Filter action buttons based on their conditions
    const visibleActionButtons = (fieldsConfig.actionButtons || []).filter(
        (button) => !button.condition || button.condition(modelData)
    );

    const {
        data: contentTypesData,
        isLoading: isLoadingContentTypes,
        error: contentTypeError,
    } = useRetrieveContentTypes({});

    // Normalize content types (handles both array and paginated formats)
    const contentTypes = Array.isArray(contentTypesData) ? contentTypesData : contentTypesData?.results || [];

    // Get content type for main model
    const mainContentTypeId = contentTypes.find(
        (ct) => ct.model?.toLowerCase() === modelType.toLowerCase()
    )?.id;

    // Get main model documents
    const {
        data: mainDocuments,
        isLoading: isLoadingMainDocs,
        error: mainDocumentError,
    } = useRetrieveDocuments(
        {
            object_id: modelData.id,
            content_type: mainContentTypeId,
        },
        undefined,
        {
            enabled: !!mainContentTypeId && !!modelData.id,
        }
    );

    // Build query configs for related model documents
    const relatedQueryConfigs = useMemo(() => {
        return (fieldsConfig.relatedModels || []).map(relatedModel => {
            const relatedId = relatedModel.getValue
                ? relatedModel.getValue(modelData)
                : modelData[relatedModel.fieldName];

            const relatedContentTypeId = contentTypes.find(
                (ct) => ct.model?.toLowerCase() === relatedModel.modelType.toLowerCase()
            )?.id;

            return {
                queryKey: ["document", { object_id: relatedId, content_type: relatedContentTypeId }],
                queryFn: () => api.api_Documents_list({ queries: { object_id: relatedId, content_type: relatedContentTypeId } }),
                enabled: !!relatedContentTypeId && !!relatedId,
            };
        });
    }, [fieldsConfig.relatedModels, modelData, contentTypes]);

    // Use batch queries for related model documents
    const relatedDocumentQueries = useQueries({ queries: relatedQueryConfigs });

    // Combine all documents with source information
    const allDocuments: DocumentWithSource[] = [
        // Main model documents
        ...(mainDocuments?.results?.map(doc => ({
            ...doc,
            file: doc.file.replace("/media/", "/media/"),
            sourceModel: modelType,
            sourceLabel: "This Record"
        })) ?? []),

        // Related model documents
        ...relatedDocumentQueries.flatMap((query, index) => {
            const relatedModel = fieldsConfig.relatedModels![index];
            return query.data?.results?.map(doc => ({
                ...doc,
                file: doc.file.replace("/media/", "/media/"),
                sourceModel: relatedModel.modelType,
                sourceLabel: relatedModel.label
            })) ?? [];
        })
    ];

    const isLoadingDocs = isLoadingMainDocs || relatedDocumentQueries.some(q => q.isLoading);
    const documentError = mainDocumentError || relatedDocumentQueries.find(q => q.error)?.error;

    const renderField = (field: string, value: any) => {
        const customRenderer = fieldsConfig.customRenderers?.[field];
        if (customRenderer) return customRenderer(value, modelData);

        if (value === null || value === undefined || value === "") {
            return <span className="text-muted-foreground italic">—</span>;
        }

        if (typeof value === "boolean") {
            return value ? "Yes" : "No";
        }

        return String(value);
    };

    // Enhanced DocumentsSection that shows source - renders docs directly without nested Card
    const EnhancedDocumentsSection = ({ documents, isLoading, onDocumentSelect, selectedDocument }) => {
        // Group documents by source
        const groupedDocuments = documents.reduce((acc, doc) => {
            const source = doc.sourceLabel || 'Unknown';
            if (!acc[source]) acc[source] = [];
            acc[source].push(doc);
            return acc;
        }, {});

        if (isLoading) {
            return (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Documents</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground">Loading documents...</p>
                    </CardContent>
                </Card>
            );
        }

        if (documents.length === 0) {
            return (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Documents</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground italic">No documents found</p>
                    </CardContent>
                </Card>
            );
        }

        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Documents</CardTitle>
                    <CardDescription>
                        Files associated with this record and related items
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {Object.entries(groupedDocuments).map(([source, docs]: [string, DocumentWithSource[]]) => (
                        <div key={source}>
                            <div className="flex items-center gap-2 mb-2">
                                <Badge variant="outline" className="text-xs">
                                    {source}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                    {docs.length} document{docs.length !== 1 ? 's' : ''}
                                </span>
                            </div>
                            <div className="space-y-2">
                                {docs.map((doc) => {
                                    const isSelected = selectedDocument?.id === doc.id;
                                    return (
                                        <div
                                            key={doc.id}
                                            className={`flex items-start gap-3 text-sm p-2 rounded-md transition-colors cursor-pointer ${
                                                isSelected ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted/50'
                                            }`}
                                            onClick={() => onDocumentSelect?.(doc)}
                                        >
                                            <div className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0">📄</div>
                                            <div className="space-y-0.5 flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className={`font-medium truncate ${isSelected ? 'text-primary' : 'text-foreground'}`}>
                                                        {doc.file_name}
                                                    </span>
                                                    <a
                                                        href={doc.file}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-primary hover:text-primary/80 text-xs underline flex-shrink-0"
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        (open)
                                                    </a>
                                                </div>
                                                <div className="text-muted-foreground text-xs">
                                                    Uploaded by {doc.uploaded_by_name || "Unknown"} on{" "}
                                                    {doc.upload_date ? new Date(doc.upload_date).toLocaleDateString() : "—"}
                                                    {doc.version && <> • v{doc.version}</>}
                                                    {doc.classification && <> • {doc.classification}</>}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </CardContent>
            </Card>
        );
    };

    const AuditComponent = fieldsConfig.subcomponents?.AuditTrailComponent || AuditTrailComponent;

    return (
        <ResizablePanelGroup direction="horizontal" className="w-full max-w-[1600px] mx-auto rounded-lg border" style={{ height: 'calc(100vh - 8rem)' }}>
            <ResizablePanel defaultSize={34} minSize={20}>
                <div className="h-full overflow-auto">
                    {/* Sticky header */}
                    <div className="sticky top-0 z-10 bg-background border-b px-6 py-4">
                        <div className="flex items-start justify-between gap-2 flex-wrap">
                            <div className="min-w-0 flex-1">
                                <h1 className="text-xl font-bold tracking-tight truncate">
                                    {modelData.name || `${modelType} Detail`}
                                </h1>
                                <p className="text-sm text-muted-foreground truncate">ID: {modelData.id}</p>
                            </div>
                            {visibleActionButtons.length > 0 && (
                                <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
                                    {visibleActionButtons.map((button, idx) => (
                                        <Button
                                            key={idx}
                                            variant={button.variant || "default"}
                                            size="sm"
                                            onClick={() => navigate({ to: button.getUrl(modelData) })}
                                        >
                                            {button.icon}
                                            {button.label}
                                        </Button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Content sections */}
                    <div className="px-6 py-4 space-y-6">
                        {fieldsConfig.sections.info.map((section, idx) => (
                            <section key={idx} className="space-y-3">
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                    {section.title}
                                </h3>
                                <div className="grid grid-cols-1 gap-y-2">
                                    {section.fields.map((field) =>
                                        field in modelData ? (
                                            <div key={field} className="flex flex-col gap-0.5 text-sm min-w-0">
                                                <span className="text-muted-foreground text-xs">
                                                    {fieldsConfig.fields[field]?.label || field}
                                                </span>
                                                <span className="text-foreground break-words" style={{ overflowWrap: 'anywhere' }}>
                                                    {renderField(field, modelData[field])}
                                                </span>
                                            </div>
                                        ) : null
                                    )}
                                </div>
                                {idx < fieldsConfig.sections.info.length - 1 && <Separator className="mt-4" />}
                            </section>
                        ))}

                        {/* Documents section */}
                        {modelType.toLowerCase() !== 'documents' && allDocuments.length > 0 && (
                            <>
                                <Separator />
                                <section className="space-y-3">
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                        Documents
                                    </h3>
                                    <div className="space-y-4">
                                        {Object.entries(
                                            allDocuments.reduce((acc, doc) => {
                                                const source = doc.sourceLabel || 'This Record';
                                                if (!acc[source]) acc[source] = [];
                                                acc[source].push(doc);
                                                return acc;
                                            }, {} as Record<string, DocumentWithSource[]>)
                                        ).map(([source, docs]) => (
                                            <div key={source}>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Badge variant="outline" className="text-xs">{source}</Badge>
                                                    <span className="text-xs text-muted-foreground">
                                                        {docs.length} file{docs.length !== 1 ? 's' : ''}
                                                    </span>
                                                </div>
                                                <div className="space-y-1">
                                                    {docs.map((doc) => {
                                                        const isSelected = selectedDocument?.id === doc.id;
                                                        return (
                                                            <div
                                                                key={doc.id}
                                                                className={`flex items-start gap-2 text-sm p-2 rounded transition-colors cursor-pointer ${
                                                                    isSelected ? 'bg-primary/10' : 'hover:bg-muted/50'
                                                                }`}
                                                                onClick={() => setSelectedDocument(doc)}
                                                            >
                                                                <span className="flex-shrink-0">📄</span>
                                                                <div className="min-w-0 flex-1">
                                                                    <div className="flex items-center gap-2">
                                                                        <span className={`truncate ${isSelected ? 'text-primary font-medium' : ''}`}>
                                                                            {doc.file_name}
                                                                        </span>
                                                                        <a
                                                                            href={doc.file}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="text-primary text-xs hover:underline flex-shrink-0"
                                                                            onClick={(e) => e.stopPropagation()}
                                                                        >
                                                                            open
                                                                        </a>
                                                                    </div>
                                                                    <div className="text-xs text-muted-foreground">
                                                                        v{doc.version || 1} • {doc.classification || 'internal'}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            </>
                        )}

                        {/* Audit trail */}
                        <Separator />
                        <section className="space-y-3">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                Activity History
                            </h3>
                            <AuditComponent objectId={modelData.id} modelType={modelType} />
                        </section>
                    </div>
                </div>
            </ResizablePanel>

            {RendererSidebarComponent && <ResizableHandle />}

            {RendererSidebarComponent && (
                <ResizablePanel defaultSize={66} minSize={30}>
                    <div className="h-full overflow-y-auto p-6 bg-muted/5">
                    <RendererSidebarComponent
                        modelType={modelType}
                        modelData={selectedDocument || modelData}
                        documents={allDocuments}
                        loading={isLoadingDocs || isLoadingContentTypes}
                    />
                    </div>
                </ResizablePanel>
            )}
        </ResizablePanelGroup>
    );
};

export default ModelDetailPage;