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
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteDocumentType } from "@/hooks/useDeleteDocumentType";
import { toast } from "sonner";

type Props = {
    documentTypeId: string;
};

export function EditDocumentTypeActionsCell({ documentTypeId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteDocumentType = useDeleteDocumentType();

    const handleEdit = () => {
        navigate({
            to: "/DocumentTypeForm/edit/$id",
            params: { id: String(documentTypeId) },
        });
    };

    const handleDelete = () => {
        deleteDocumentType.mutate(documentTypeId, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Document type deleted successfully.");
            },
            onError: (error) => {
                console.error("Failed to delete document type:", error);
                toast.error("Failed to delete document type.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Document Type"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Document Type"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Document Type?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. Documents of this type
                            will retain their type but new documents cannot use it.
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
