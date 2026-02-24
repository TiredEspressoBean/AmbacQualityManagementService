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
import { Pencil, Archive } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useUpdatePart } from "@/hooks/useUpdatePart";
import {toast} from "sonner"; // <- adjust path as needed

type Props = {
    partId: string;
};

export function EditPartActionsCell({ partId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const updatePart = useUpdatePart();

    const handleEditPart = () => {
        navigate({
            to: "/PartForm/edit/$id", // <- adjust if your edit route differs
            params: { id: String(partId) },
        });
    };

    const archivePart = () => {
        updatePart.mutate(
            {
                id: partId,
                data:{archived:true} as any
            },
            {
                onSuccess: () => {
                    setOpen(false);
                    toast.success(`Part #${partId} deleted successfully.`);
                },
            }
        );
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditPart}
                title="Edit Part"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Archive Part"
                    >
                        <Archive className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Archive Part #{partId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The part will be removed from active tracking.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={archivePart}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Confirm Archive
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
