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
import {Button} from "@/components/ui/button";
import {Pencil, Delete} from "lucide-react";
import {useNavigate} from "@tanstack/react-router";
import {useState} from "react";
import {useDeletePartType} from "@/hooks/useDeletePartType.ts";
import {toast} from "sonner"; // <- adjust path as needed

type Props = {
    partTypeId: string;
};

export function EditPartTypeActionsCell({partTypeId}: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deletePartType = useDeletePartType();

    const handleEditPart = () => {
        navigate({
            to: "/PartTypeForm/edit/$id", // <- adjust if your edit route differs
            params: {id: String(partTypeId)},
        });
    };

    const deletingPartType = () => {
        deletePartType.mutate(partTypeId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Part Type #${partTypeId} deleted successfully.`);
            },
        });
    };

    return (<div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditPart}
                title="Edit Part"
            >
                <Pencil className="h-4 w-4"/>
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Part Type"
                    >
                        <Delete className="h-4 w-4"/>
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Part Type #{partTypeId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The part will be removed from active tracking.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={deletingPartType}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Confirm Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>);
}
