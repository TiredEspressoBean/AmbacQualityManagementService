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
import { Pencil, Delete } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteStep } from "@/hooks/useDeleteStep"; // <- hook for deleting steps
import { toast } from "sonner";

type Props = {
    stepId: string;
};

export function EditStepActionsCell({ stepId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteStep = useDeleteStep();

    const handleEditStep = () => {
        navigate({
            to: "/StepForm/edit/$id",
            params: { id: String(stepId) },
        });
    };

    const handleDelete = () => {
        deleteStep.mutate(stepId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Step #${stepId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete step:", error);
                toast.error("Failed to delete step.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditStep}
                title="Edit Step"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Step"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Step #{stepId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The step will be removed from the associated process.
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
