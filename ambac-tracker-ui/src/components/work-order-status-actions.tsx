import { useState } from "react";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Button } from "@/components/ui/button";
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
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { PlayCircle, PauseCircle, XCircle, RotateCcw, Undo2 } from "lucide-react";
import { usePlaceOnHoldWorkOrder } from "@/hooks/usePlaceOnHoldWorkOrder";
import { useClearHoldWorkOrder } from "@/hooks/useClearHoldWorkOrder";
import { HOLD_REASONS, type HoldReason } from "@/pages/workorders/constants";
import type { WorkOrderHold } from "@/components/workorders/WorkOrderHoldBanner";
import { ClearHoldDialog } from "@/components/workorders/ClearHoldDialog";
import { useCancelWorkOrder, useReleaseForScheduling, useUnreleaseForScheduling } from "@/hooks/useScheduling";
import { ShortCloseDialog } from "@/components/workorders/ShortCloseDialog";
import { apiErrorBlockers } from "@/lib/api/describeApiError";
import { apiErrorStatus } from "@/lib/api-error";
import { toast } from "sonner";
import type { WorkOrderStatusEnum } from "@/lib/api/generated";

type WorkOrderStatus = WorkOrderStatusEnum;

type Props = {
    workOrderId: string;
    currentStatus: WorkOrderStatus;
    /** When the work order was released for scheduling; null if it has not been. */
    releasedAt?: string | null;
    /** The open hold, so Resume can say what it is clearing. */
    currentHold?: WorkOrderHold | null;
    onStatusChange?: () => void;
};


/**
 * Status action buttons for work orders.
 * Shows available actions based on current status.
 */
export function WorkOrderStatusActions({
    workOrderId,
    currentStatus,
    releasedAt,
    currentHold,
    onStatusChange,
}: Props) {
    const [holdDialogOpen, setHoldDialogOpen] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [shortCloseOpen, setShortCloseOpen] = useState(false);
    const [holdReason, setHoldReason] = useState<HoldReason | "">("");
    const [holdDetails, setHoldDetails] = useState("");
    const [releaseBlockers, setReleaseBlockers] = useState<string[]>([]);
    const [overrideReason, setOverrideReason] = useState("");

    // Status isn't written directly (the server refuses it on an edit): each move has
    // its action. A hold records its reason; clearing it returns the order to where
    // the work is; cancel checks nothing has shipped and cascades to the order.
    const placeOnHold = usePlaceOnHoldWorkOrder();
    const clearHold = useClearHoldWorkOrder();
    const cancelWorkOrder = useCancelWorkOrder();
    const busy = placeOnHold.isPending || clearHold.isPending || cancelWorkOrder.isPending;

    const handleHold = () => {
        if (!holdReason) {
            toast.error("Please select a hold reason");
            return;
        }
        placeOnHold.mutate(
            { id: workOrderId, reason: holdReason, notes: holdDetails.trim() || undefined },
            {
                onSuccess: () => {
                    toast.success("Work order placed on hold");
                    setHoldDialogOpen(false);
                    setHoldReason("");
                    setHoldDetails("");
                    onStatusChange?.();
                },
            }
        );
    };

    const [resumeOpen, setResumeOpen] = useState(false);
    const handleResume = (notes: string) => {
        clearHold.mutate({ id: workOrderId, notes }, {
            onSuccess: () => {
                toast.success("Hold cleared");
                setResumeOpen(false);
                onStatusChange?.();
            },
        });
    };

    // Release authorizes the order for scheduling (services/mes/release.py): it runs the
    // readiness check and records who released it and when. It does not touch the
    // status — that moves to In progress when work actually starts. A failing check
    // comes back 409 with its blockers; releasing anyway needs a written reason.
    const release = useReleaseForScheduling();
    const unrelease = useUnreleaseForScheduling();

    const handleRelease = (override_reason?: string) => {
        release.mutate(
            { id: workOrderId, override_reason },
            {
                onSuccess: () => {
                    setReleaseBlockers([]);
                    setOverrideReason("");
                    onStatusChange?.();
                },
                onError: (e) => {
                    if (apiErrorStatus(e) === 409) setReleaseBlockers(apiErrorBlockers(e));
                },
            }
        );
    };

    const handleUnrelease = () => {
        unrelease.mutate(workOrderId, { onSuccess: () => onStatusChange?.() });
    };

    const { has: hasPerm } = usePermissionSet();

    const handleCancel = () => {
        cancelWorkOrder.mutate(workOrderId, { onSuccess: () => onStatusChange?.() });
        setCancelDialogOpen(false);
    };

    // Determine available actions based on current status
    // Release, hold and resume all change the order — the server gates them on
    // change_workorder, so they aren't offered without it.
    const canChange = hasPerm("change_workorder");
    const canRelease = canChange && !releasedAt && currentStatus !== "ON_HOLD";
    const canUnrelease = canChange && !!releasedAt;
    const canHold = canChange && (currentStatus === "IN_PROGRESS" || currentStatus === "PENDING");
    const canResume = canChange && currentStatus === "ON_HOLD";
    // Status alone isn't enough: cancelling abandons a commitment to a customer,
    // so the server gates it on `cancel_workorder` (manager tier). Mirror that here
    // rather than offering a button the API will refuse.
    const canCancel =
        currentStatus !== "COMPLETED" &&
        currentStatus !== "CANCELLED" &&
        hasPerm("cancel_workorder");
    const isReadOnly = currentStatus === "COMPLETED" || currentStatus === "CANCELLED";

    if (isReadOnly) {
        return null;
    }

    return (
        <div className="flex items-center gap-2">
            {/* Release Button */}
            {canRelease && (
                <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleRelease()}
                    disabled={release.isPending}
                >
                    <PlayCircle className="h-4 w-4 mr-2" />
                    Release
                </Button>
            )}
            {canUnrelease && (
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleUnrelease}
                    disabled={unrelease.isPending}
                >
                    <Undo2 className="h-4 w-4 mr-2" />
                    Un-release
                </Button>
            )}
            <Dialog
                open={releaseBlockers.length > 0}
                onOpenChange={(open) => {
                    if (!open) {
                        setReleaseBlockers([]);
                        setOverrideReason("");
                    }
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Not ready to release</DialogTitle>
                        <DialogDescription>
                            The schedule would not be able to plan this work order as written. Fix
                            these, or release anyway with a reason — the reason is recorded on the
                            work order.
                        </DialogDescription>
                    </DialogHeader>
                    <ul className="list-disc space-y-1 pl-5 text-sm">
                        {releaseBlockers.map((b) => (
                            <li key={b}>{b}</li>
                        ))}
                    </ul>
                    <div className="space-y-2">
                        <Label htmlFor="release-override">Reason to release anyway</Label>
                        <Textarea
                            id="release-override"
                            placeholder="e.g. Operator certification completes Friday"
                            value={overrideReason}
                            onChange={(e) => setOverrideReason(e.target.value)}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setReleaseBlockers([])}>
                            Cancel
                        </Button>
                        <Button
                            onClick={() => handleRelease(overrideReason.trim())}
                            disabled={!overrideReason.trim() || release.isPending}
                        >
                            Release anyway
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Hold Button */}
            {canHold && (
                <Dialog open={holdDialogOpen} onOpenChange={setHoldDialogOpen}>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setHoldDialogOpen(true)}
                        disabled={busy}
                    >
                        <PauseCircle className="h-4 w-4 mr-2" />
                        Hold
                    </Button>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Put Work Order on Hold</DialogTitle>
                            <DialogDescription>
                                Select a reason for placing this work order on hold.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="hold-reason">Reason</Label>
                                <Select
                                    value={holdReason}
                                    onValueChange={(value) => setHoldReason(value as HoldReason)}
                                >
                                    <SelectTrigger id="hold-reason">
                                        <SelectValue placeholder="Select a reason" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {HOLD_REASONS.map((reason) => (
                                            <SelectItem key={reason.value} value={reason.value}>
                                                {reason.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            {holdReason !== "" && (
                                <div className="space-y-2">
                                    <Label htmlFor="hold-details">Details</Label>
                                    <Textarea
                                        id="hold-details"
                                        placeholder={holdReason === "OTHER" ? "What is the hold for?" : "Optional details"}
                                        value={holdDetails}
                                        onChange={(e) => setHoldDetails(e.target.value)}
                                    />
                                </div>
                            )}
                        </div>
                        <DialogFooter>
                            <Button
                                variant="outline"
                                onClick={() => setHoldDialogOpen(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleHold}
                                disabled={!holdReason || busy}
                            >
                                Confirm Hold
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            )}

            {/* Resume Button */}
            {canResume && (
                <>
                    <Button variant="default" size="sm" disabled={busy} onClick={() => setResumeOpen(true)}>
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Resume
                    </Button>
                    <ClearHoldDialog open={resumeOpen} onOpenChange={setResumeOpen} hold={currentHold}
                                     pending={clearHold.isPending} onConfirm={handleResume} />
                </>
            )}

            {/* Short-close: complete with fewer built than planned (same gate as Cancel). */}
            {canCancel && currentStatus !== "ON_HOLD" && (
                <>
                    <Button variant="ghost" size="sm" disabled={busy} onClick={() => setShortCloseOpen(true)}>
                        Short-close
                    </Button>
                    <ShortCloseDialog
                        workOrderId={workOrderId}
                        open={shortCloseOpen}
                        onOpenChange={setShortCloseOpen}
                        onDone={() => onStatusChange?.()}
                    />
                </>
            )}

            {/* Cancel Button */}
            {canCancel && (
                <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                    <AlertDialogTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            disabled={busy}
                        >
                            <XCircle className="h-4 w-4 mr-2" />
                            Cancel
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Cancel Work Order?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This action will cancel the work order. This cannot be undone.
                                It drops out of scheduling; its parts stay on it. To carry unfinished
                                parts to other work, short-close it instead.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Go Back</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={handleCancel}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                                Confirm Cancel
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            )}
        </div>
    );
}
