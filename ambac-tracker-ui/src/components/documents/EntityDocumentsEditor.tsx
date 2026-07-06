"use client";

import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { FileText, Upload, Trash2, Loader2, ExternalLink, FileIcon, ChevronsUpDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { useCreateDocument } from "@/hooks/useCreateDocument";
import { useDeleteDocuments } from "@/hooks/useDeleteDocuments";
import { useRetrieveDocumentTypes } from "@/hooks/useRetrieveDocumentTypes";
import { useContentTypeMapping } from "@/hooks/useContentTypes";

export interface EntityDocumentsEditorProps {
    /** Django model name (lowercase) for the content type, e.g. "materiallot". */
    contentTypeModel: string;
    /** Object id (uuid) the documents attach to. */
    objectId: string;
    /** Dialog title context, e.g. a lot number. */
    label: string;
    description?: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    readOnly?: boolean;
}

type Doc = {
    id: string; file_name: string; file_url?: string;
    document_type_code?: string; status?: string; version?: number;
};

function statusBadge(status: string) {
    const s = status.toUpperCase();
    if (s === "APPROVED" || s === "RELEASED") return <Badge className="bg-green-600">{status}</Badge>;
    if (s === "UNDER_REVIEW") return <Badge variant="outline" className="border-amber-600 text-amber-600">{status}</Badge>;
    if (s === "OBSOLETE") return <Badge variant="destructive">{status}</Badge>;
    return <Badge variant="secondary">{status}</Badge>;
}

/** Reusable attach/list/upload documents dialog for any model with a Documents
 *  GenericRelation. Generalized from the flow-editor step documents editor. */
export function EntityDocumentsEditor({
    contentTypeModel, objectId, label, description, open, onOpenChange, readOnly = false,
}: EntityDocumentsEditorProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [fileName, setFileName] = useState("");
    const [docType, setDocType] = useState("");
    const [docTypeOpen, setDocTypeOpen] = useState(false);

    const { getContentTypeId, isLoading: ctLoading } = useContentTypeMapping();
    const contentTypeId = getContentTypeId(contentTypeModel);

    const { data: documentsData, isLoading, refetch } = useRetrieveDocuments(
        { content_type: contentTypeId, object_id: objectId },
        undefined,
        { enabled: open && !!contentTypeId && !ctLoading },
    );
    const { data: docTypesData } = useRetrieveDocumentTypes();
    const documentTypes: Array<{ id: string; name: string; code: string }> = docTypesData?.results || [];

    const createDocument = useCreateDocument();
    const deleteDocument = useDeleteDocuments();
    const documents = (documentsData?.results || []) as Doc[];

    const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) { setSelectedFile(file); setFileName(file.name.replace(/\.[^/.]+$/, "")); }
    };

    const upload = async () => {
        if (!selectedFile || !contentTypeId) return;
        setIsUploading(true);
        try {
            const payload: Record<string, unknown> = {
                file: selectedFile, file_name: fileName || selectedFile.name,
                content_type: contentTypeId, object_id: objectId, classification: "INTERNAL",
            };
            if (docType) payload.document_type = docType;
            await createDocument.mutateAsync(payload as never);
            toast.success("Document uploaded");
            setSelectedFile(null); setFileName(""); setDocType("");
            if (fileInputRef.current) fileInputRef.current.value = "";
            refetch();
        } catch {
            toast.error("Failed to upload document");
        } finally {
            setIsUploading(false);
        }
    };

    const remove = async (id: string) => {
        try { await deleteDocument.mutateAsync(id); toast.success("Document removed"); refetch(); }
        catch { toast.error("Failed to remove document"); }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl max-h-[85vh] p-0 gap-0">
                <DialogHeader className="p-6 pb-0">
                    <DialogTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" /> Documents — {label}
                    </DialogTitle>
                    <DialogDescription>{description ?? "Attach certificates, reports, and supporting documents."}</DialogDescription>
                </DialogHeader>

                <ScrollArea className="max-h-[calc(85vh-10rem)]">
                    <div className="p-6 pt-4 space-y-6">
                        {!readOnly && (
                            <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                                <Label className="text-sm font-medium">Upload new document</Label>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label className="text-xs">Document type</Label>
                                        <Popover open={docTypeOpen} onOpenChange={setDocTypeOpen}>
                                            <PopoverTrigger asChild>
                                                <Button variant="outline" role="combobox" className="w-full justify-between font-normal">
                                                    {docType ? documentTypes.find((d) => String(d.id) === docType)?.name ?? "Select type…" : "Select type…"}
                                                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                                </Button>
                                            </PopoverTrigger>
                                            <PopoverContent className="w-[220px] p-0">
                                                <Command>
                                                    <CommandInput placeholder="Search types…" />
                                                    <CommandList>
                                                        <CommandEmpty>No document type found.</CommandEmpty>
                                                        {documentTypes.map((d) => (
                                                            <CommandItem key={d.id} value={`${d.name} ${d.code}`}
                                                                onSelect={() => { setDocType(String(d.id)); setDocTypeOpen(false); }}>
                                                                <Check className={cn("mr-2 h-4 w-4", docType === String(d.id) ? "opacity-100" : "opacity-0")} />
                                                                {d.name} ({d.code})
                                                            </CommandItem>
                                                        ))}
                                                    </CommandList>
                                                </Command>
                                            </PopoverContent>
                                        </Popover>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs">Display name</Label>
                                        <Input value={fileName} onChange={(e) => setFileName(e.target.value)} placeholder="Document name" />
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <input ref={fileInputRef} type="file" onChange={onPickFile} className="hidden"
                                        accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif" />
                                    <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                                        <Upload className="h-4 w-4 mr-2" /> Select file
                                    </Button>
                                    {selectedFile && <span className="text-sm text-muted-foreground truncate max-w-[200px]">{selectedFile.name}</span>}
                                    <Button type="button" onClick={upload} disabled={!selectedFile || isUploading} className="ml-auto">
                                        {isUploading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Uploading…</> : "Upload"}
                                    </Button>
                                </div>
                            </div>
                        )}

                        {!readOnly && <Separator />}

                        <div className="space-y-3">
                            <Label className="text-sm font-medium">Attached documents ({documents.length})</Label>
                            {isLoading ? (
                                <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
                            ) : documents.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground border rounded-md">
                                    <FileIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                    <p>No documents attached.</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {documents.map((doc) => (
                                        <div key={doc.id} className="flex items-center gap-3 p-3 rounded-md border bg-card hover:bg-accent/50">
                                            <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-sm truncate">{doc.file_name}</span>
                                                    {doc.document_type_code && <Badge variant="outline" className="text-xs shrink-0">{doc.document_type_code}</Badge>}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    {doc.status && statusBadge(doc.status)}
                                                    {doc.version && <span>v{doc.version}</span>}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 shrink-0">
                                                {doc.file_url && (
                                                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8" asChild>
                                                        <a href={doc.file_url} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-4 w-4" /></a>
                                                    </Button>
                                                )}
                                                {!readOnly && (
                                                    <AlertDialog>
                                                        <AlertDialogTrigger asChild>
                                                            <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive">
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </AlertDialogTrigger>
                                                        <AlertDialogContent>
                                                            <AlertDialogHeader>
                                                                <AlertDialogTitle>Remove document</AlertDialogTitle>
                                                                <AlertDialogDescription>Remove "{doc.file_name}"? This deletes the document.</AlertDialogDescription>
                                                            </AlertDialogHeader>
                                                            <AlertDialogFooter>
                                                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                                <AlertDialogAction onClick={() => remove(doc.id)} className="bg-destructive text-destructive-foreground">Remove</AlertDialogAction>
                                                            </AlertDialogFooter>
                                                        </AlertDialogContent>
                                                    </AlertDialog>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </ScrollArea>

                <div className="p-6 pt-0 flex justify-end">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
