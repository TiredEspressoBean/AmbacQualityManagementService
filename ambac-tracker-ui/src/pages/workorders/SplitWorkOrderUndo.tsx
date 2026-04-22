import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Undo2 } from "lucide-react";

export function UndoSplitButton({ onUndo, isPending }: { onUndo: () => void; isPending?: boolean }) {
    const [confirmOpen, setConfirmOpen] = useState(false);
    return (
        <>
            <Button variant="outline" size="sm" onClick={() => setConfirmOpen(true)} disabled={isPending}>
                <Undo2 className="mr-1 h-3 w-3" />
                {isPending ? "Undoing…" : "Undo split"}
            </Button>
            <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Undo split?</DialogTitle>
                        <DialogDescription>
                            Parts return to the parent WO. This child WO is closed. The split
                            event remains in the audit log for traceability.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            disabled={isPending}
                            onClick={() => {
                                onUndo();
                                setConfirmOpen(false);
                            }}
                        >
                            Undo split
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
