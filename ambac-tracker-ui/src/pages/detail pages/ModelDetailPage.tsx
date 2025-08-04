import React, { useState } from "react";
import {
    Card, CardHeader, CardTitle, CardContent, CardDescription,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import DocumentsSection from "@/pages/detail pages/DocumentsSection";
import AuditTrailComponent from "@/pages/detail pages/AuditTrail";

type InfoSection = {
    title: string;
    fields: string[];
    auditLog?: boolean;
};

type RelatedModel = {
    modelType: string;
    fieldName: string; // The field that contains the related model ID
    label: string; // Display name for the relationship
    getValue?: (modelData: any) => number | null; // Custom getter for the related ID
};

type FieldsConfig = {
    fields: Record<string, { label: string }>;
    customRenderers?: Record<string, (value: any) => React.ReactNode>;
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
    id: number;
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

    const {
        data: contentTypes,
        isLoading: isLoadingContentTypes,
        error: contentTypeError,
    } = useRetrieveContentTypes({});

    // Get content type for main model
    const mainContentTypeId = contentTypes?.results?.find(
        (ct) => ct.model?.toLowerCase() === modelType.toLowerCase()
    )?.id;

    // Get main model documents
    const {
        data: mainDocuments,
        isLoading: isLoadingMainDocs,
        error: mainDocumentError,
    } = useRetrieveDocuments(
        {
            queries: {
                object_id: modelData.id,
                content_type: mainContentTypeId,
            },
        },
        {
            enabled: !!mainContentTypeId && !!modelData.id,
        }
    );

    // Hook for each related model's documents
    const relatedDocumentQueries = (fieldsConfig.relatedModels || []).map(relatedModel => {
        const relatedId = relatedModel.getValue
            ? relatedModel.getValue(modelData)
            : modelData[relatedModel.fieldName];

        const relatedContentTypeId = contentTypes?.results?.find(
            (ct) => ct.model?.toLowerCase() === relatedModel.modelType.toLowerCase()
        )?.id;

        return useRetrieveDocuments(
            {
                queries: {
                    object_id: relatedId,
                    content_type: relatedContentTypeId,
                },
            },
            {
                enabled: !!relatedContentTypeId && !!relatedId,
            }
        );
    });

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
        if (customRenderer) return customRenderer(value);

        if (value === null || value === undefined || value === "") {
            return <span className="text-muted-foreground italic">—</span>;
        }

        if (typeof value === "boolean") {
            return value ? "Yes" : "No";
        }

        return String(value);
    };

    // Enhanced DocumentsSection that shows source
    const EnhancedDocumentsSection = ({ documents, isLoading, error, onDocumentSelect, selectedDocument }) => {
        const DocumentsSectionComponent = fieldsConfig.subcomponents?.DocumentsSectionComponent || DocumentsSection;

        // Group documents by source
        const groupedDocuments = documents.reduce((acc, doc) => {
            const source = doc.sourceLabel || 'Unknown';
            if (!acc[source]) acc[source] = [];
            acc[source].push(doc);
            return acc;
        }, {});

        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Documents</CardTitle>
                    <CardDescription>
                        Files associated with this record and related items
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {Object.entries(groupedDocuments).map(([source, docs]) => (
                        <div key={source} className="mb-6 last:mb-0">
                            <div className="flex items-center gap-2 mb-3">
                                <Badge variant="outline" className="text-xs">
                                    {source}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                    {docs.length} document{docs.length !== 1 ? 's' : ''}
                                </span>
                            </div>
                            <DocumentsSectionComponent
                                documents={docs}
                                isLoading={isLoading}
                                error={error}
                                onDocumentSelect={onDocumentSelect}
                                selectedDocument={selectedDocument}
                                hideHeader={true} // Don't show the header since we're grouping
                            />
                        </div>
                    ))}

                    {documents.length === 0 && !isLoading && (
                        <p className="text-muted-foreground italic">No documents found</p>
                    )}
                </CardContent>
            </Card>
        );
    };

    const AuditComponent = fieldsConfig.subcomponents?.AuditTrailComponent || AuditTrailComponent;

    return (
        <ResizablePanelGroup direction="horizontal" className="w-full max-w-[1600px] mx-auto rounded-lg border">
            <ResizablePanel defaultSize={34} minSize={20} className="p-6">
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle>
                            <div className="flex flex-col gap-1">
                                <h1 className="text-xl font-bold tracking-tight">
                                    {modelData.name || `${modelType} Detail`}
                                </h1>
                                <p className="text-sm text-muted-foreground">ID: {modelData.id}</p>
                            </div>
                        </CardTitle>
                    </CardHeader>

                    <CardContent className="space-y-8">
                        {fieldsConfig.sections.info.map((section, idx) => (
                            <section key={idx} className="space-y-4">
                                <div className="space-y-1">
                                    <h3 className="text-lg font-semibold tracking-wide text-foreground">
                                        {section.title}
                                    </h3>
                                    <CardDescription className="text-sm text-muted-foreground" />
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                                    {section.fields.map((field) =>
                                        field in modelData ? (
                                            <div key={field} className="flex flex-col gap-1 text-sm">
                                                <span className="text-muted-foreground font-medium">
                                                    {fieldsConfig.fields[field]?.label || field}
                                                </span>
                                                <span className="text-foreground break-words">
                                                    {renderField(field, modelData[field])}
                                                </span>
                                            </div>
                                        ) : null
                                    )}
                                </div>

                                {idx < fieldsConfig.sections.info.length - 1 && <Separator />}
                            </section>
                        ))}

                        <EnhancedDocumentsSection
                            documents={allDocuments}
                            isLoading={isLoadingDocs || isLoadingContentTypes}
                            error={documentError || contentTypeError}
                            onDocumentSelect={setSelectedDocument}
                            selectedDocument={selectedDocument}
                        />

                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Activity History</CardTitle>
                                <CardDescription>Recent changes and updates to this record</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <AuditComponent objectId={modelData.id} modelType={modelType} />
                            </CardContent>
                        </Card>
                    </CardContent>
                </Card>
            </ResizablePanel>

            {RendererSidebarComponent && <ResizableHandle />}

            {RendererSidebarComponent && (
                <ResizablePanel defaultSize={66} minSize={30} className="p-6 bg-muted/5">
                    <RendererSidebarComponent
                        modelType={modelType}
                        modelData={selectedDocument || modelData}
                        documents={allDocuments}
                        loading={isLoadingDocs || isLoadingContentTypes}
                    />
                </ResizablePanel>
            )}
        </ResizablePanelGroup>
    );
};

export default ModelDetailPage;