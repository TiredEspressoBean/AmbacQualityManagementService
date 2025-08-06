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
import { useDeleteUser } from "@/hooks/useDeleteUser.ts";
import { toast } from "sonner";

type Props = {
    userId: number;
};

export function EditUserActionsCell({ userId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteUser = useDeleteUser();

    const handleEditUser = () => {
        navigate({
            to: "/UserForm/edit/$id",
            params: { id: String(userId) },
        });
    };

    const handleDelete = () => {
        deleteUser.mutate(userId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`User #${userId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete user:", error);
                toast.error("Failed to delete user.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditUser}
                title="Edit User"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete User"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete User #{userId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The user will be removed from the system and lose access to all resources.
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