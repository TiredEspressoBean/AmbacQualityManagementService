import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { FileIcon, Package, Settings, ClipboardList } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { z } from "zod";
import type { schemas } from "@/lib/api/generated";
import { useQaDocuments } from "@/hooks/useQaDocuments";
import { useState, useEffect } from "react";
import DocumentRenderer from "@/pages/detail pages/DocumentRenderer";

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
        <Card className="h-full">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <FileIcon className="h-5 w-5" />
                        Documents
                        <span className="text-sm font-normal text-muted-foreground">
                            ({allDocuments.length})
                        </span>
                    </CardTitle>
                    {selectedDocument && (
                        <a
                            href={selectedDocument.file}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:text-primary/80 text-sm underline"
                        >
                            Open externally ↗
                        </a>
                    )}
                </div>
                
                {Object.keys(docsBySource).length > 0 && (
                    <Tabs value={activeDocumentTab} onValueChange={setActiveDocumentTab} className="w-full">
                        <TabsList className="grid w-full grid-cols-3">
                            {Object.entries(docsBySource).map(([source, docs]) => (
                                <TabsTrigger 
                                    key={source} 
                                    value={source}
                                    className="flex items-center gap-1 text-xs"
                                >
                                    {getSourceIcon(source)}
                                    <span className="hidden md:inline">{source}</span>
                                    <span className="bg-background/80 text-muted-foreground px-1 py-0.5 rounded text-xs">
                                        {docs.length}
                                    </span>
                                </TabsTrigger>
                            ))}
                        </TabsList>
                        
                        {/* Simple dropdown for document selection within active tab */}
                        {Object.entries(docsBySource).map(([source, docs]) => (
                            <TabsContent key={source} value={source} className="mt-2">
                                {docs.length > 1 ? (
                                    <select 
                                        className="w-full p-2 border rounded-md text-sm bg-background"
                                        value={selectedDocument?.id || ""}
                                        onChange={(e) => {
                                            const doc = docs.find(d => d.id?.toString() === e.target.value);
                                            if (doc) setSelectedDocument(doc);
                                        }}
                                    >
                                        <option value="">Select document...</option>
                                        {docs.map((doc) => (
                                            <option key={doc.id} value={doc.id}>
                                                {doc.file_name} {doc.classification && `(${doc.classification})`}
                                            </option>
                                        ))}
                                    </select>
                                ) : docs.length === 1 ? (
                                    <div className="text-sm text-muted-foreground p-3 bg-muted/20 rounded border">
                                        Showing: <span className="font-medium ml-1">{docs[0].file_name}</span>
                                    </div>
                                ) : null}
                            </TabsContent>
                        ))}
                    </Tabs>
                )}
            </CardHeader>
            
            <CardContent className="h-[calc(100%-160px)] overflow-hidden p-0">
                {selectedDocument ? (
                    <div className="h-full">
                        <DocumentRenderer 
                            modelData={{
                                file: selectedDocument.file,
                                file_name: selectedDocument.file_name,
                                upload_date: selectedDocument.upload_date
                            }} 
                        />
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground p-6">
                        <div className="text-center space-y-2">
                            <FileIcon className="h-12 w-12 mx-auto opacity-50" />
                            <p className="text-sm">
                                {allDocuments.length > 0 
                                    ? "Select a document category above"
                                    : "No documents found"
                                }
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}