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
    /** Its number (QR-…), how a person knows it; the id is the fallback. */
    reportNumber?: string | null;
};

export function EditQualityReportActionsCell({ qualityReportId, reportNumber }: Props) {
    const name = `Inspection record ${reportNumber || qualityReportId}`;
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteQualityReport = useDeleteQualityReport();

    const handleEdit = () => {
        navigate({
            to: "/editor/quality-reports/$id/edit",
            params: { id: String(qualityReportId) },
        });
    };

    const handleDelete = () => {
        deleteQualityReport.mutate(qualityReportId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`${name} deleted.`);
            },
            onError: (error) => {
                console.error("Failed to delete quality report:", error);
                toast.error(`Couldn't delete ${name}`);
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit inspection record"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete inspection record"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete {name}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            It&rsquo;s archived, not erased: its history is kept and it can be restored from Data Management.
                            It no longer shows in the lists.
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
