import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { FileIcon, Package, Settings, ClipboardList, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { z } from "zod";
import type { schemas } from "@/lib/api/generated";
import { useQaDocuments } from "@/hooks/useQaDocuments";
import { useState, useEffect } from "react";
import DocumentRenderer from "@/pages/detail pages/DocumentRenderer";
import { ScrollArea } from "@/components/ui/scroll-area";

type Document = z.infer<typeof schemas.Documents>;
type WorkOrder = z.infer<typeof schemas.WorkOrder>;
type DocumentWithSource = Document & { source?: string };

type Props = {
    workOrder: WorkOrder;
    currentStepId?: number; // ID of the step currently being completed (not used with new API)
};

export function QaDocumentsSection({ workOrder }: Props) {
    const [allDocuments, setAllDocuments] = useState<DocumentWithSource[]>([]);
    const [selectedDocument, setSelectedDocument] = useState<DocumentWithSource | null>(null);
    const [activeDocumentTab, setActiveDocumentTab] = useState<string>("");

    // Use the new QA-specific documents endpoint
    const { data: qaDocumentsData, isLoading, error: queryError } = useQaDocuments(workOrder.id);

    useEffect(() => {
        if (qaDocumentsData && !isLoading) {
            try {
                const combinedDocs: DocumentWithSource[] = [];

                // Add work order docs
                if (qaDocumentsData.work_order_documents) {
                    combinedDocs.push(...qaDocumentsData.work_order_documents.map((doc: any) => ({ 
                        ...doc, 
                        source: 'Work Order' as const 
                    })));
                }

                // Add current step docs
                if (qaDocumentsData.current_step_documents) {
                    combinedDocs.push(...qaDocumentsData.current_step_documents.map((doc: any) => ({ 
                        ...doc, 
                        source: 'Current Step' as const 
                    })));
                }

                // Add part type docs
                if (qaDocumentsData.part_type_documents) {
                    combinedDocs.push(...qaDocumentsData.part_type_documents.map((doc: any) => ({ 
                        ...doc, 
                        source: 'Part Type' as const 
                    })));
                }

                // Remove duplicates by id and sort by source priority
                const uniqueDocs = combinedDocs
                    .filter((doc, index, self) => 
                        index === self.findIndex(d => d.id === doc.id)
                    )
                    .sort((a, b) => {
                        const sourcePriority = { 'Work Order': 1, 'Current Step': 2, 'Part Type': 3 };
                        return sourcePriority[a.source] - sourcePriority[b.source];
                    });

                setAllDocuments(uniqueDocs);
                
                // Set first available tab as active
                const sources = Array.from(new Set(uniqueDocs.map(doc => doc.source || 'Other')));
                if (!activeDocumentTab && sources.length > 0) {
                    setActiveDocumentTab(sources[0]);
                }
                
                // Auto-select first document if none selected
                if (!selectedDocument && uniqueDocs.length > 0) {
                    setSelectedDocument(uniqueDocs[0]);
                }
            } catch (err) {
                console.error('Failed to process QA documents:', err);
                setAllDocuments([]);
            }
        }
    }, [qaDocumentsData, isLoading, selectedDocument, activeDocumentTab]);

    const getSourceIcon = (source: string) => {
        switch (source) {
            case 'Work Order': return <ClipboardList className="h-4 w-4" />;
            case 'Current Step': return <Settings className="h-4 w-4" />;
            case 'Part Type': return <Package className="h-4 w-4" />;
            default: return <FileIcon className="h-4 w-4" />;
        }
    };

    if (isLoading) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Documents & References</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="flex items-center gap-3">
                            <Skeleton className="h-6 w-6 rounded" />
                            <Skeleton className="h-4 w-[200px]" />
                        </div>
                    ))}
                </CardContent>
            </Card>
        );
    }

    if (queryError) {
        return (
            <Alert variant="destructive">
                <AlertTitle>Failed to load documents</AlertTitle>
                <AlertDescription>Unable to fetch documents for QA: {queryError.message || 'Unknown error'}</AlertDescription>
            </Alert>
        );
    }

    if (!allDocuments || allDocuments.length === 0) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Documents & References</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground italic">
                        No documents found for this work order, current step, or part type.
                    </p>
                </CardContent>
            </Card>
        );
    }

    // Group documents by source
    const docsBySource = allDocuments.reduce((acc, doc) => {
        const source = doc.source || 'Other';
        if (!acc[source]) acc[source] = [];
        acc[source].push(doc);
        return acc;
    }, {} as Record<string, DocumentWithSource[]>);

    return (
        <div className="h-full flex flex-col space-y-2">
            {/* Compact Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <FileIcon className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-semibold text-sm">Documents</h3>
                    <Badge variant="secondary" className="text-xs">{allDocuments.length}</Badge>
                </div>
                {selectedDocument && (
                    <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="h-7 text-xs px-2"
                    >
                        <a
                            href={selectedDocument.file}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            Open
                        </a>
                    </Button>
                )}
            </div>

            {/* Document Selector - More Compact */}
            <Select
                value={selectedDocument?.id?.toString() || ""}
                onValueChange={(value) => {
                    const doc = allDocuments.find(d => d.id?.toString() === value);
                    if (doc) setSelectedDocument(doc);
                }}
            >
                <SelectTrigger className="h-9">
                    <SelectValue placeholder="Select a document..." />
                </SelectTrigger>
                <SelectContent>
                    {Object.entries(docsBySource).map(([source, docs]) => (
                        <div key={source}>
                            <div className="flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground">
                                {getSourceIcon(source)}
                                {source}
                            </div>
                            {docs.map((doc) => (
                                <SelectItem key={doc.id} value={doc.id.toString()}>
                                    <div className="flex items-center gap-2">
                                        <span className="truncate max-w-[300px]">{doc.file_name}</span>
                                        {doc.classification && (
                                            <Badge variant="outline" className="text-xs">
                                                {doc.classification}
                                            </Badge>
                                        )}
                                    </div>
                                </SelectItem>
                            ))}
                        </div>
                    ))}
                </SelectContent>
            </Select>

            {/* Document Viewer */}
            <div className="flex-1 min-h-0 rounded-lg border overflow-hidden bg-muted/10">
                {selectedDocument ? (
                    <DocumentRenderer
                        modelData={{
                            file: selectedDocument.file,
                            file_name: selectedDocument.file_name,
                            upload_date: selectedDocument.upload_date
                        }}
                    />
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        <div className="text-center space-y-2">
                            <FileIcon className="h-12 w-12 mx-auto opacity-50" />
                            <p className="text-sm">Select a document to view</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}