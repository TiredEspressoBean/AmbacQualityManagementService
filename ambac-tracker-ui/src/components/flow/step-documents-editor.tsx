"use client";

import { useState, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { FileText, Upload, Trash2, Loader2, ExternalLink, FileIcon, ChevronsUpDown, Check } from 'lucide-react';
import { useRetrieveDocuments } from '@/hooks/useRetrieveDocuments';
import { useCreateDocument } from '@/hooks/useCreateDocument';
import { useDeleteDocuments } from '@/hooks/useDeleteDocuments';
import { useRetrieveDocumentTypes } from '@/hooks/useRetrieveDocumentTypes';
import { useContentTypeMapping } from '@/hooks/useContentTypes';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export interface StepDocumentsEditorProps {
  stepId: string;
  stepName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  readOnly?: boolean;
}


export function StepDocumentsEditor({
  stepId,
  stepName,
  open,
  onOpenChange,
  readOnly = false,
}: StepDocumentsEditorProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<string>('');
  const [fileName, setFileName] = useState('');
  const [docTypeOpen, setDocTypeOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { getContentTypeId, isLoading: contentTypesLoading } = useContentTypeMapping();
  const stepsContentTypeId = getContentTypeId('steps');

  // Fetch documents for this step
  const { data: documentsData, isLoading: documentsLoading, refetch } = useRetrieveDocuments(
    {
      queries: {
        content_type: stepsContentTypeId,
        object_id: stepId,
      },
    },
    {
      enabled: open && !!stepsContentTypeId && !contentTypesLoading,
    }
  );

  // Fetch document types
  const { data: docTypesData } = useRetrieveDocumentTypes();
  const documentTypes: Array<{ id: string; name: string; code: string }> = docTypesData?.results || [];

  const createDocument = useCreateDocument();
  const deleteDocument = useDeleteDocuments();

  const documents = (documentsData?.results || []) as Array<{
    id: string;
    file_name: string;
    file_url: string;
    document_type_code?: string;
    status?: string;
    version?: number;
  }>;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setFileName(file.name.replace(/\.[^/.]+$/, '')); // Remove extension for display name
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !stepsContentTypeId) return;

    setIsUploading(true);
    try {
      const payload: any = {
        file: selectedFile,
        file_name: fileName || selectedFile.name,
        content_type: stepsContentTypeId,
        object_id: stepId,
        classification: 'internal',
      };
      if (selectedDocType) {
        payload.document_type = selectedDocType;
      }

      await createDocument.mutateAsync(payload);

      toast.success('Document uploaded');
      setSelectedFile(null);
      setFileName('');
      setSelectedDocType('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      refetch();
    } catch (error) {
      console.error('Failed to upload document:', error);
      toast.error('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument.mutateAsync(documentId);
      toast.success('Document removed');
      refetch();
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Failed to remove document');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'RELEASED':
        return <Badge variant="default" className="bg-green-600">{status}</Badge>;
      case 'DRAFT':
        return <Badge variant="secondary">{status}</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="outline" className="text-amber-600 border-amber-600">{status}</Badge>;
      case 'OBSOLETE':
        return <Badge variant="destructive">{status}</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] p-0 gap-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Documents for "{stepName}"
          </DialogTitle>
          <DialogDescription>
            Attach work instructions, SOPs, drawings, specs, and other documents to this step
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[calc(85vh-10rem)]">
          <div className="p-6 pt-4 space-y-6">
            {/* Upload Section - hidden in readOnly mode */}
            {!readOnly && (
            <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
              <Label className="text-sm font-medium">Upload New Document</Label>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="doc-type" className="text-xs">Document Type</Label>
                  <Popover open={docTypeOpen} onOpenChange={setDocTypeOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={docTypeOpen}
                        className="w-full justify-between font-normal"
                      >
                        {selectedDocType
                          ? documentTypes.find((dt) => String(dt.id) === selectedDocType)?.name || 'Select type...'
                          : 'Select type...'}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[200px] p-0">
                      <Command>
                        <CommandInput placeholder="Search types..." />
                        <CommandList>
                          <CommandEmpty>No document type found.</CommandEmpty>
                          {documentTypes.map((dt) => (
                            <CommandItem
                              key={dt.id}
                              value={`${dt.name} ${dt.code}`}
                              onSelect={() => {
                                setSelectedDocType(String(dt.id));
                                setDocTypeOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedDocType === String(dt.id) ? "opacity-100" : "opacity-0"
                                )}
                              />
                              {dt.name} ({dt.code})
                            </CommandItem>
                          ))}
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="file-name" className="text-xs">Display Name</Label>
                  <Input
                    id="file-name"
                    value={fileName}
                    onChange={(e) => setFileName(e.target.value)}
                    placeholder="Document name"
                  />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Select File
                </Button>
                {selectedFile && (
                  <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                    {selectedFile.name}
                  </span>
                )}
                <Button
                  type="button"
                  onClick={handleUpload}
                  disabled={!selectedFile || isUploading}
                  className="ml-auto"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    'Upload'
                  )}
                </Button>
              </div>
            </div>
            )}

            {!readOnly && <Separator />}

            {/* Documents List */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">
                Attached Documents ({documents.length})
              </Label>

              {documentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border rounded-md">
                  <FileIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No documents attached to this step.</p>
                  <p className="text-sm">Upload a work instruction to get started.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-3 p-3 rounded-md border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <FileText className="h-5 w-5 text-muted-foreground shrink-0" />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">
                            {doc.file_name}
                          </span>
                          {doc.document_type_code && (
                            <Badge variant="outline" className="text-xs shrink-0">
                              {doc.document_type_code}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {doc.status && getStatusBadge(doc.status)}
                          {doc.version && <span>v{doc.version}</span>}
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {doc.file_url && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            asChild
                          >
                            <a href={doc.file_url} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </Button>
                        )}

                        {!readOnly && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Remove Document</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to remove "{doc.file_name}" from this step?
                                This will delete the document.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(doc.id)}
                                className="bg-destructive text-destructive-foreground"
                              >
                                Remove
                              </AlertDialogAction>
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

        <div className="p-6 pt-0">
          <div className="flex justify-end">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
