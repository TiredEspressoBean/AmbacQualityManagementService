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
import { useDeleteQualityReport } from "@/hooks/useDeleteQualityReport.ts";
import { toast } from "sonner";

type Props = {
    qualityReportId: string;
};

export function EditQualityReportActionsCell({ qualityReportId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteQualityReport = useDeleteQualityReport();

    const handleEdit = () => {
        navigate({
            to: "/editor/qualityReports/edit/$id",
            params: { id: String(qualityReportId) },
        });
    };

    const handleDelete = () => {
        deleteQualityReport.mutate(qualityReportId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Quality Report #${qualityReportId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete quality report:", error);
                toast.error(`Failed to delete Quality Report #${qualityReportId}`);
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Quality Report"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Quality Report"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Quality Report #{qualityReportId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action is permanent and cannot be undone.
                            The quality report will be removed from the system.
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
