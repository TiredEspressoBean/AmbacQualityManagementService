import {
    AlertDialog,
    AlertDialogTrigger,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogFooter,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogCancel,
    AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteJobRole } from "@/hooks/useDeleteJobRole";
import { toast } from "sonner";

type Props = {
    roleId: string;
};

export function EditJobRoleActionCell({ roleId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteRole = useDeleteJobRole();

    const handleEdit = () => {
        navigate({ to: "/quality/training/roles/$roleId/edit", params: { roleId: String(roleId) } });
    };

    const handleDelete = () => {
        deleteRole.mutate({ id: roleId }, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Job role deleted successfully.");
            },
            onError: (error) => {
                console.error("Failed to delete job role:", error);
                toast.error("Failed to delete job role.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={handleEdit} title="Edit Job Role">
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-destructive" title="Delete Job Role">
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Job Role?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. Users assigned to this role will keep their
                            training but lose their role-based required-competency profile.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
