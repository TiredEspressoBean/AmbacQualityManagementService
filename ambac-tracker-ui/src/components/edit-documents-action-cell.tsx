import {
    AlertDialog,
    AlertDialogTrigger,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogFooter,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogCancel,
    AlertDialogAction
} from "@/components/ui/alert-dialog.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Pencil, Delete } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteDocuments } from "@/hooks/useDeleteDocuments.ts"; // <- hook for deleting documents
import { toast } from "sonner";

type Props = {
    documentId: number;
};

export function EditDocumentsActionsCell({ documentId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteDocument = useDeleteDocuments();

    const handleEditDocument = () => {
        navigate({
            to: "/DocumentForm/edit/$id",
            params: { id: String(documentId) },
        });
    };

    const handleDelete = () => {
        deleteDocument.mutate(documentId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Document #${documentId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete document:", error);
                toast.error("Failed to delete document.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditDocument}
                title="Edit Document"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Document"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Document #{documentId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The document will be removed from the associated process.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Confirm Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
