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
import {Button} from "@/components/ui/button";
import {Pencil, Delete, Truck} from "lucide-react";
import {usePermissionSet} from "@/hooks/useMyPermissions";
import {PartTypeSourcingDialog} from "@/components/part-types/PartTypeSourcingDialog";
import {useNavigate} from "@tanstack/react-router";
import {useState} from "react";
import {useDeletePartType} from "@/hooks/useDeletePartType.ts";
import {toast} from "sonner"; // <- adjust path as needed

type Props = {
    partTypeId: string;
};

export function EditPartTypeActionsCell({partTypeId}: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deletePartType = useDeletePartType();
    // A buyer's way in: sourcing only, without the part-authoring permission.
    const {has} = usePermissionSet();
    const [sourcingOpen, setSourcingOpen] = useState(false);

    const handleEditPart = () => {
        navigate({
            to: "/editor/part-types/$id/edit", // <- adjust if your edit route differs
            params: {id: String(partTypeId)},
        });
    };

    const deletingPartType = () => {
        deletePartType.mutate(partTypeId, {
            onSuccess: () => {
                setOpen(false);
                toast.success("Part type archived.");
            },
        });
    };

    return (<div className="flex items-center gap-1">
            {has("change_parttype_sourcing") && (
                <>
                    <Button variant="ghost" size="icon" onClick={() => setSourcingOpen(true)}
                        title="Sourcing — supplier, lead time, safety stock">
                        <Truck className="h-4 w-4"/>
                    </Button>
                    {sourcingOpen && (
                        <PartTypeSourcingDialog partTypeId={String(partTypeId)} open={sourcingOpen}
                            onOpenChange={setSourcingOpen}/>
                    )}
                </>
            )}
            {/* Only what this user may do: a buyer (sourcing only) was offered Edit and
                Delete, and got an error for trying. */}
            {has("change_parttypes") && (
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEditPart}
                title="Edit Part"
            >
                <Pencil className="h-4 w-4"/>
            </Button>
            )}
            {has("delete_parttypes") && (
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Part Type"
                    >
                        <Delete className="h-4 w-4"/>
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Archive this part type?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            It leaves the active lists, and its history is kept. It can be
                            restored from Data Management.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={deletingPartType}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Archive
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
            )}
        </div>);
}
