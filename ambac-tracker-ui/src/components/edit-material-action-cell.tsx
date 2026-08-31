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
import { Pencil, Delete } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useDeleteMaterial } from "@/hooks/useMaterials";

type Props = { materialId: string; name?: string };

export function EditMaterialActionsCell({ materialId, name }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const del = useDeleteMaterial();

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                title="Edit material"
                onClick={() => navigate({ to: "/editor/materials/$id/edit", params: { id: String(materialId) } })}
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-destructive" title="Delete material">
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete {name ? `"${name}"` : "material"}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This is permanent. BOM lines that buy this material will lose their
                            component reference. Prefer marking it inactive if it has history.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => del.mutate(materialId, { onSuccess: () => setOpen(false) })}
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
