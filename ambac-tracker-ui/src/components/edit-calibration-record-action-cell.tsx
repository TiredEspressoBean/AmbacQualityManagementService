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
import { useDeleteCalibrationRecord } from "@/hooks/useDeleteCalibrationRecord";
import { toast } from "sonner";

type Props = {
    recordId: string;
};

export function EditCalibrationRecordActionCell({ recordId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteRecord = useDeleteCalibrationRecord();

    const handleEdit = () => {
        navigate({
            to: "/CalibrationRecordForm/$id",
            params: { id: String(recordId) },
        });
    };

    const handleDelete = () => {
        deleteRecord.mutate({ id: recordId }, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Calibration record deleted successfully.");
            },
            onError: (error) => {
                console.error("Failed to delete calibration record:", error);
                toast.error("Failed to delete calibration record.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Calibration Record"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Calibration Record"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Calibration Record?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. The calibration record will be permanently deleted.
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
