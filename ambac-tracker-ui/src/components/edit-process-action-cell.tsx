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
import {useDeleteProcesses} from "@/hooks/useDeleteProcess.ts";
import {toast} from "sonner"; // <- adjust path as needed

type Props = {
    processId: number;
};

export function EditProcessActionsCell({processId}: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteProcess = useDeleteProcesses();

    const handleEditPart = () => {
        navigate({
            to: "/ProcessForm/edit/$id", // <- adjust if your edit route differs
            params: {id: String(processId)},
        });
    };

    const deletingProcess = () => {
        deleteProcess.mutate(processId, {
            onSuccess: () => {
                setOpen(false);
                console.log(`Part ${processId} deleted`);
                toast.success(`Part Type #${processId} deleted successfully.`);
            }, onError: (error) => {
                console.error("Failed to archive part:", error);
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
                        Delete Part Type #{processId}?
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                        This action is permanent and cannot be undone.
                        The part will be removed from active tracking.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={deletingProcess}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        Confirm Delete
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    </div>);
}
