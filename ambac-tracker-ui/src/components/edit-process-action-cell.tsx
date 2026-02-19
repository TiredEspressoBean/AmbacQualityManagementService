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
import {Delete, Workflow} from "lucide-react";
import {useNavigate} from "@tanstack/react-router";
import {useState} from "react";
import {useDeleteProcesses} from "@/hooks/useDeleteProcess.ts";
import {toast} from "sonner";

type Props = {
    processId: string;
};

export function EditProcessActionsCell({processId}: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteProcess = useDeleteProcesses();

    const handleEditFlow = () => {
        navigate({
            to: "/process-flow",
            search: { id: processId },
        });
    };

    const deletingProcess = () => {
        deleteProcess.mutate(processId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Process deleted successfully.`);
            }, onError: (error) => {
                console.error("Failed to delete process:", error);
            },
        });
    };

    return (<div className="flex items-center gap-1">
        <Button
            variant="ghost"
            size="icon"
            onClick={handleEditFlow}
            title="Edit Process"
        >
            <Workflow className="h-4 w-4"/>
        </Button>
        <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    title="Delete Process"
                >
                    <Delete className="h-4 w-4"/>
                </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>
                        Delete this process?
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                        This action is permanent and cannot be undone.
                        The process will be removed.
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
