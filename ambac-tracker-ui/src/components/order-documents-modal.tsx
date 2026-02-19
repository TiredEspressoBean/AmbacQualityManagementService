import { useState } from "react";
import { format } from "date-fns";
import {
    File, FileText, Image, FileSpreadsheet, Download,
    Search, X, Loader2
} from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useScopedDocuments } from "@/hooks/useScopedDocuments";

interface Document {
    id: string;
    file_name: string;
    file_url: string | null;
    upload_date: string;
    is_image: boolean;
}

interface OrderDocumentsModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    orderId: string;
    orderName: string;
}

function getFileIcon(doc: Document) {
    if (doc.is_image) {
        return <Image className="h-4 w-4 text-blue-500" />;
    }
    if (doc.file_name.endsWith('.pdf')) {
        return <FileText className="h-4 w-4 text-red-500" />;
    }
    if (doc.file_name.match(/\.(xlsx?|csv)$/i)) {
        return <FileSpreadsheet className="h-4 w-4 text-green-600" />;
    }
    return <File className="h-4 w-4 text-muted-foreground" />;
}

function DocumentRow({ doc }: { doc: Document }) {
    const content = (
        <>
            {getFileIcon(doc)}
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.file_name}</p>
                <p className="text-xs text-muted-foreground">
                    {format(new Date(doc.upload_date), "MMM d, yyyy")}
                </p>
            </div>
            {doc.file_url && (
                <Download className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
        </>
    );

    if (doc.file_url) {
        return (
            <a
                href={doc.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-muted/50 transition-colors group"
            >
                {content}
            </a>
        );
    }

    return (
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-md text-muted-foreground">
            {content}
        </div>
    );
}

export function OrderDocumentsModal({ open, onOpenChange, orderId, orderName }: OrderDocumentsModalProps) {
    const [searchQuery, setSearchQuery] = useState("");

    // Fetch documents from order's scope (includes all descendants)
    const { data: documents = [], isLoading } = useScopedDocuments("orders", orderId, {
        enabled: open, // Only fetch when modal is open
    });

    // Filter documents based on search
    const filteredDocuments = searchQuery.trim()
        ? documents.filter(d =>
            d.file_name.toLowerCase().includes(searchQuery.toLowerCase())
        )
        : documents;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg h-[80vh] flex flex-col overflow-hidden">
                <DialogHeader className="pb-2">
                    <DialogTitle className="flex items-center gap-2 text-base">
                        <File className="h-4 w-4" />
                        Documents
                    </DialogTitle>
                    <p className="text-sm text-muted-foreground">{orderName}</p>
                </DialogHeader>

                {/* Search - only show if more than a few docs */}
                {documents.length > 5 && (
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 h-9"
                        />
                        {searchQuery && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                                onClick={() => setSearchQuery("")}
                            >
                                <X className="h-3 w-3" />
                            </Button>
                        )}
                    </div>
                )}

                {/* Document list */}
                <ScrollArea className="h-[400px]">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : filteredDocuments.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground text-sm">
                            {searchQuery ? "No documents match your search" : "No documents attached"}
                        </div>
                    ) : (
                        <div className="space-y-0.5 py-2 pr-4">
                            {filteredDocuments.map(doc => (
                                <DocumentRow key={doc.id} doc={doc} />
                            ))}
                        </div>
                    )}
                </ScrollArea>

                {/* Footer */}
                {filteredDocuments.length > 0 && (
                    <div className="pt-3 border-t text-xs text-muted-foreground text-center">
                        {searchQuery
                            ? `${filteredDocuments.length} of ${documents.length} documents`
                            : `${documents.length} documents`}
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}
