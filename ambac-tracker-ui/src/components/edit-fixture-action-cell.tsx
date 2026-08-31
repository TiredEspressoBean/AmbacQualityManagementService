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
import { useDeleteFixture } from "@/hooks/useScheduling";

type Props = { fixtureId: string; name?: string };

export function EditFixtureActionsCell({ fixtureId, name }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const del = useDeleteFixture();

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                title="Edit resource"
                onClick={() => navigate({ to: "/editor/tooling/$id/edit", params: { id: String(fixtureId) } })}
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-destructive" title="Delete resource">
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete {name ? `"${name}"` : "resource"}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This is permanent. Steps that required this resource will no longer be
                            constrained by it on the next solve.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => del.mutate(fixtureId, { onSuccess: () => setOpen(false) })}
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
