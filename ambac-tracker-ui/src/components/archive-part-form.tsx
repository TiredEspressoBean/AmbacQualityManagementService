import * as React from "react";
import { useForm } from "@tanstack/react-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { useUpdatePart } from "@/hooks/useUpdatePart"; // adjust path as needed

export function ArchivePartDialog({ partId }: { partId: string }) {
    const [open, setOpen] = React.useState(false);
    const { mutateAsync: updatePart } = useUpdatePart({ query: { archived: false } });

    const form = useForm({
        defaultValues: {},
        onSubmit: async () => {
            try {
                await updatePart({
                    id: partId,
                    data: { archived: true } as any,
                });
                toast.success("Part archived");
                setOpen(false);
            } catch (err) {
                toast.error("Failed to archive part");
                console.error(err);
            }
        },
    });

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                    Archive
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Archive Part</DialogTitle>
                </DialogHeader>

                <form
                    onSubmit={(e) => {
                        e.preventDefault();
                        form.handleSubmit();
                    }}
                    className="space-y-4"
                >
                    <p>Are you sure you want to archive this part?</p>

                    <DialogFooter>
                        <Button
                            type="submit"
                            variant="destructive"
                            disabled={form.state.isSubmitting}
                        >
                            {form.state.isSubmitting ? "Archiving..." : "Confirm"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
