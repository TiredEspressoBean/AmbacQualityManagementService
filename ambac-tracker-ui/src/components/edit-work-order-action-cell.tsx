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
import {useDeleteWorkOrder} from "@/hooks/useDeleteWorkOrder.ts";
import {toast} from "sonner"; // <- adjust path as needed

type Props = {
    workOrderId: string;
};

export function EditWorkOrderActionsCell({workOrderId}: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteWorkOrder = useDeleteWorkOrder();

    const handleEditWorkOrder = () => {
        navigate({
            to: "/WorkOrderForm/edit/$id", // <- adjust if your edit route differs
            params: {id: String(workOrderId)},
        });
    };

    const deletingWorkOrder = () => {
        deleteWorkOrder.mutate(workOrderId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`WorkOrder #${workOrderId} deleted successfully.`);
            },
        });
    };

    return (<div className="flex items-center gap-1">
        <Button
            variant="ghost"
            size="icon"
            onClick={handleEditWorkOrder}
            title="Edit Work Order"
        >
            <Pencil className="h-4 w-4"/>
        </Button>
        <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    title="Delete Work Order"
                >
                    <Delete className="h-4 w-4"/>
                </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>
                        Delete Work Order #{workOrderId}?
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                        This action is permanent and cannot be undone.
                        The part will be removed from active tracking.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={deletingWorkOrder}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        Confirm Delete
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    </div>);
}
