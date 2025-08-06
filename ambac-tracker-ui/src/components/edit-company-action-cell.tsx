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
import { useDeleteCompany } from "@/hooks/useDeleteCompany.ts";
import { toast } from "sonner";

type Props = {
    companyId: number;
};

export function EditCompanyActionsCell({ companyId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteCompany = useDeleteCompany();

    const handleEditCompany = () => {
        navigate({
            to: "/CompaniesForm/edit/$id",
            params: { id: String(companyId) },
        });
    };

    const handleDelete = () => {
        deleteCompany.mutate(companyId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Company #${companyId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete company:", error);
                toast.error("Failed to delete company.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditCompany}
                title="Edit Company"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Company"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Company #{companyId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The company will be removed from the system.
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