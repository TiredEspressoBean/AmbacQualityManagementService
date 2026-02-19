import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    FileInput,
    FileUploader,
    FileUploaderContent,
    FileUploaderItem,
} from "@/components/ui/file-upload";
import { CloudUpload, Paperclip, Loader2 } from "lucide-react";
import { useReviseDocument } from "@/hooks/useReviseDocument";

interface DocumentRevisionModalProps {
    documentId: string;
    documentName: string;
    isOpen: boolean;
    onClose: () => void;
}

export function DocumentRevisionModal({
    documentId,
    documentName,
    isOpen,
    onClose,
}: DocumentRevisionModalProps) {
    const navigate = useNavigate();
    const [changeJustification, setChangeJustification] = useState("");
    const [files, setFiles] = useState<File[] | null>(null);
    const { mutate: reviseDocument, isPending } = useReviseDocument();

    const handleSubmit = () => {
        if (!changeJustification.trim()) {
            toast.error("Please provide a reason for this revision");
            return;
        }

        reviseDocument(
            {
                id: documentId,
                change_justification: changeJustification.trim(),
                file: files?.[0],
                file_name: files?.[0]?.name,
            },
            {
                onSuccess: (data: any) => {
                    toast.success("New revision created successfully");
                    onClose();
                    setChangeJustification("");
                    setFiles(null);
                    // Navigate to the new version
                    if (data?.id) {
                        navigate({ to: "/documents/$id", params: { id: String(data.id) } });
                    }
                },
                onError: (error: any) => {
                    const message = error?.response?.data?.error || "Failed to create revision";
                    toast.error(message);
                },
            }
        );
    };

    const handleClose = () => {
        if (!isPending) {
            setChangeJustification("");
            setFiles(null);
            onClose();
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Create New Revision</DialogTitle>
                    <DialogDescription>
                        Create a new version of "{documentName}". The current version will be
                        preserved in the version history.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="justification">Change Justification *</Label>
                        <Textarea
                            id="justification"
                            placeholder="Describe what changed and why..."
                            value={changeJustification}
                            onChange={(e) => setChangeJustification(e.target.value)}
                            rows={3}
                            disabled={isPending}
                        />
                        <p className="text-xs text-muted-foreground">
                            This will be recorded in the document history for audit purposes.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label>New File (Optional)</Label>
                        <FileUploader
                            value={files}
                            onValueChange={setFiles}
                            dropzoneOptions={{ maxFiles: 1, maxSize: 1024 * 1024 * 10 }}
                            className="relative bg-background rounded-lg p-2"
                        >
                            <FileInput
                                id="revisionFileInput"
                                className="outline-dashed outline-1 outline-slate-500"
                            >
                                <div className="flex items-center justify-center flex-col p-4 w-full">
                                    <CloudUpload className="text-gray-500 w-8 h-8" />
                                    <p className="text-sm text-gray-500 dark:text-gray-400">
                                        <span className="font-semibold">Click to upload</span> or drag and drop
                                    </p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">
                                        Leave empty to keep the current file
                                    </p>
                                </div>
                            </FileInput>
                            <FileUploaderContent>
                                {files?.map((file, i) => (
                                    <FileUploaderItem key={i} index={i}>
                                        <Paperclip className="h-4 w-4 stroke-current" />
                                        <span>{file.name}</span>
                                    </FileUploaderItem>
                                ))}
                            </FileUploaderContent>
                        </FileUploader>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isPending}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={isPending}>
                        {isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        Create Revision
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
