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
import { useDeleteErrorType } from "@/hooks/useDeleteErrorType.ts"; // <- hook for deleting errorTypes
import { toast } from "sonner";

type Props = {
    errorTypeId: string;
};

export function EditErrorTypeActionsCell({ errorTypeId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteErrorType = useDeleteErrorType();

    const handleEditErrorType = () => {
        navigate({
            to: "/ErrorTypeForm/edit/$id",
            params: { id: String(errorTypeId) },
        });
    };

    const handleDelete = () => {
        deleteErrorType.mutate(errorTypeId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`ErrorType #${errorTypeId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete errorType:", error);
                toast.error("Failed to delete errorType.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditErrorType}
                title="Edit ErrorType"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete ErrorType"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Error Type #{errorTypeId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The error type will be removed from the associated process.
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
