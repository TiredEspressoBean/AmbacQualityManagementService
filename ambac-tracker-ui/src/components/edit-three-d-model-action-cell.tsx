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
import { useDeleteThreeDModel } from "@/hooks/useDeleteThreeDModel.ts";
import { toast } from "sonner";

type Props = {
    modelId: string;
};

export function EditThreeDModelActionsCell({ modelId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteModel = useDeleteThreeDModel();

    const handleEditModel = () => {
        navigate({
            to: "/ThreeDModelsForm/edit/$id",
            params: { id: String(modelId) },
        });
    };

    const handleDelete = () => {
        deleteModel.mutate(modelId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`3D Model #${modelId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete 3D model:", error);
                toast.error("Failed to delete 3D model.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditModel}
                title="Edit 3D Model"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete 3D Model"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete 3D Model #{modelId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The 3D model will be removed from the system.
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
