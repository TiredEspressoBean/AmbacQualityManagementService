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
import { useDeleteSamplingRule } from "@/hooks/useDeleteSamplingRule";
import { toast } from "sonner";

type Props = {
    ruleId: number;
};

export function EditSamplingRuleActionsCell({ ruleId }: Props) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const deleteRule = useDeleteSamplingRule();

    const handleEdit = () => {
        navigate({
            to: "/SamplingRuleForm/edit/$id",
            params: { id: String(ruleId) },
        });
    };

    const handleDelete = () => {
        deleteRule.mutate(ruleId, {
            onSuccess: () => {
                setOpen(false);
                toast.success(`Sampling Rule #${ruleId} deleted successfully.`);
            },
            onError: (error) => {
                console.error("Failed to delete sampling rule:", error);
                toast.error("Failed to delete sampling rule.");
            },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleEdit}
                title="Edit Sampling Rule"
            >
                <Pencil className="h-4 w-4" />
            </Button>
            <AlertDialog open={open} onOpenChange={setOpen}>
                <AlertDialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        title="Delete Sampling Rule"
                    >
                        <Delete className="h-4 w-4" />
                    </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete Sampling Rule #{ruleId}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. The rule will be removed
                            from its associated ruleset.
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
