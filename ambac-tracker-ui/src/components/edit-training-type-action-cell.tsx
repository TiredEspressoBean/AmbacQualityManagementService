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
import { useDeleteTrainingType } from "@/hooks/useDeleteTrainingType";
import { toast } from "sonner";

type Props = {
    typeId: string;
};

export function EditTrainingTypeActionCell({ typeId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteType = useDeleteTrainingType();

    const handleEdit = () => {
        navigate({
            to: "/TrainingTypeForm/$id",
            params: { id: String(typeId) },
        });
    };

    const handleDelete = () => {
        deleteType.mutate({ id: typeId }, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Training type deleted successfully.");
            },
            onError: (error) => {
                console.error("Failed to delete training type:", error);
                toast.error("Failed to delete training type.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Training Type"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Training Type"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Training Type?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. The training type will be permanently deleted.
                            Any training records using this type will be affected.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
