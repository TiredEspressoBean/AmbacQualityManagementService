import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/** Scrap ends a part's life the moment it's recorded: every scrap decision is confirmed
 *  here, the same way wherever it's made (disposition form, NCR decide). */
export function ScrapConfirmDialog({ open, onOpenChange, what, onConfirm }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** What is scrapped: a part's serial, or "3 parts". */
    what: string;
    onConfirm: () => void;
}) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Scrap {what}?</AlertDialogTitle>
                    <AlertDialogDescription>
                        Scrapped as soon as this is saved. While a disposition is still open, its
                        decision can be changed, with a reason, which un-scraps the part.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        onClick={onConfirm}
                    >
                        Scrap
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
