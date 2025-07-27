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
import { useDeleteEquipment } from "@/hooks/useDeleteEquipment.ts"; // <- hook for deleting equipments
import { toast } from "sonner";

type Props = {
    equipmentId: number;
};

export function EditEquipmentActionsCell({ equipmentId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteEquipment = useDeleteEquipment();

    const handleEditEquipment = () => {
        navigate({
            to: "/EquipmentForm/edit/$id",
            params: { id: String(equipmentId) },
        });
    };

    const handleDelete = () => {
        deleteEquipment.mutate(equipmentId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Equipment #${equipmentId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete equipment:", error);
                toast.error("Failed to delete equipment.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditEquipment}
                title="Edit Equipment"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Equipment"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Equipment #{equipmentId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The equipment will be removed from the associated process.
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
