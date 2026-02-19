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
import { Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteApprovalTemplate } from "@/hooks/useDeleteApprovalTemplate";
import { toast } from "sonner";

type Props = {
    templateId: string;
};

export function EditApprovalTemplateActionsCell({ templateId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteTemplate = useDeleteApprovalTemplate();

    const handleEdit = () => {
        navigate({
            to: "/ApprovalTemplateForm/edit/$id",
            params: { id: String(templateId) },
        });
    };

    const handleDelete = () => {
        deleteTemplate.mutate(templateId, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Approval template deleted successfully.");
            },
            onError: (error) => {
                console.error("Failed to delete template:", error);
                toast.error("Failed to delete approval template.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Template"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Template"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Approval Template?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. Existing approval requests
                            using this template will not be affected, but no new
                            requests can use this template.
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
