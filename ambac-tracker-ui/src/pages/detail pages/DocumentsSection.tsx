import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { FileIcon } from "lucide-react";
import {z} from "zod";
import type {schemas} from "@/lib/api/generated.ts"; // or any icon

type Document = z.infer<typeof schemas.Document>;

type Props = {
    documents: Document[];
    isLoading?: boolean;
    error?: unknown;
    onDocumentSelect?: (document: Document) => void;
    selectedDocument?: Document | null;
};

const DocumentsSection: React.FC<Props> = ({ documents, isLoading, error, onDocumentSelect, selectedDocument }) => {
    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Documents</CardTitle>
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

    if (error) {
        return (
            <Alert variant="destructive">
                <AlertTitle>Failed to load documents</AlertTitle>
                <AlertDescription>Please try again later.</AlertDescription>
            </Alert>
        );
    }

    if (!documents || documents.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Documents</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground italic">No documents attached.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Documents</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {documents.map((doc) => {
                    const isSelected = selectedDocument?.id === doc.id;
                    return (
                        <div 
                            key={doc.id} 
                            className={`flex items-start gap-3 text-sm p-2 rounded-md transition-colors cursor-pointer ${
                                isSelected ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted/50'
                            }`}
                            onClick={() => onDocumentSelect?.(doc)}
                        >
                            <FileIcon className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                            <div className="space-y-0.5 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className={`font-medium ${isSelected ? 'text-primary' : 'text-foreground'}`}>
                                        {doc.file_name}
                                    </span>
                                    <a
                                        href={doc.file}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-primary hover:text-primary/80 text-xs underline"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        (open)
                                    </a>
                                </div>
                                <div className="text-muted-foreground text-xs">
                                    Uploaded by {doc.uploaded_by_name || "Unknown"} on{" "}
                                    {doc.upload_date
                                        ? new Date(doc.upload_date).toLocaleDateString()
                                        : "—"}
                                    {doc.version && <> • v{doc.version}</>}
                                    {doc.classification && <> • {doc.classification}</>}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </CardContent>
        </Card>
    );
};

export default DocumentsSection;
