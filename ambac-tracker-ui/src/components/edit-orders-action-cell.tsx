import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger
} from "@/components/ui/alert-dialog";
import {Button} from "@/components/ui/button";
import {Archive, Pencil, Settings} from "lucide-react";
import {useNavigate} from "@tanstack/react-router";
import {useState} from "react";
import {useUpdateOrder} from "@/hooks/useUpdateOrder";

type Props = {
    orderId: string;
};

export function EditOrderActionsCell({ orderId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const updateOrder = useUpdateOrder();

    const handleEditOrder = () => {
        navigate({
            to: "/OrderForm/$id",
            params: { id: String(orderId) },
        });
    };

    const handleEditParts = () => {
        navigate({
            to: "/editOrdersParts/$orderId",
            params: { orderId: String(orderId) },
        });
    };

    const archiveOrder = () => {
        updateOrder.mutate(
            {
                id: orderId,
                newData: {
                    archived:true
                } as any
            },
            {
                onSuccess: () => {
                    setOpen(false);
                    console.log(`Order ${orderId} archived`);
                },
                onError: (error) => {
                    console.error("Failed to archive order:", error);
                },
            }
        );
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditOrder}
                title="Edit Order"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditParts}
                title="Edit Parts"
            >
                <Settings className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Archive Order"
                    >
                        <Archive className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Archive Order #{orderId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The order will be removed from active tracking.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={archiveOrder}
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
