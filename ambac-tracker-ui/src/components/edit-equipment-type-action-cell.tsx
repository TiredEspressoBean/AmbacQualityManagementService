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
import { useDeleteEquipmentType } from "@/hooks/useDeleteEquipmentType.ts"; // <- hook for deleting equipmentTypes
import { toast } from "sonner";

type Props = {
    equipmentTypeId: string;
};

export function EditEquipmentTypeActionsCell({ equipmentTypeId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteEquipmentType = useDeleteEquipmentType();

    const handleEditEquipmentType = () => {
        navigate({
            to: "/EquipmentTypeForm/edit/$id",
            params: { id: String(equipmentTypeId) },
        });
    };

    const handleDelete = () => {
        deleteEquipmentType.mutate(equipmentTypeId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`EquipmentType #${equipmentTypeId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete equipmentType:", error);
                toast.error("Failed to delete equipmentType.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditEquipmentType}
                title="Edit EquipmentType"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete EquipmentType"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Equipment Type #{equipmentTypeId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The equipment type will be removed from the associated process.
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
