import { useState } from "react";
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
import { PlayCircle, PauseCircle, XCircle, RotateCcw } from "lucide-react";
import { useUpdateWorkOrder } from "@/hooks/useUpdateWorkOrder";
import { toast } from "sonner";
import type { WorkOrderStatusEnum } from "@/lib/api/generated";

type WorkOrderStatus = WorkOrderStatusEnum;

type Props = {
    workOrderId: string;
    currentStatus: WorkOrderStatus;
    currentNotes?: string | null;
    onStatusChange?: () => void;
};

const HOLD_REASONS = [
    { value: "material_shortage", label: "Material shortage" },
    { value: "equipment_issue", label: "Equipment issue" },
    { value: "quality_hold", label: "Quality hold" },
    { value: "engineering_review", label: "Engineering review" },
    { value: "customer_request", label: "Customer request" },
    { value: "other", label: "Other" },
] as const;

type HoldReasonValue = typeof HOLD_REASONS[number]["value"];

/**
 * Status action buttons for work orders.
 * Shows available actions based on current status.
 */
export function WorkOrderStatusActions({
    workOrderId,
    currentStatus,
    currentNotes,
    onStatusChange,
}: Props) {
    const [holdDialogOpen, setHoldDialogOpen] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
    const [holdReason, setHoldReason] = useState<HoldReasonValue | "">("");
    const [holdDetails, setHoldDetails] = useState("");

    const updateWorkOrder = useUpdateWorkOrder();

    const updateStatus = (
        newStatus: WorkOrderStatus,
        notePrefix?: string
    ) => {
        const timestamp = new Date().toISOString().split("T")[0];
        let updatedNotes = currentNotes || "";

        if (notePrefix) {
            updatedNotes = `[${notePrefix} - ${timestamp}]\n${updatedNotes}`;
        }

        updateWorkOrder.mutate(
            {
                id: workOrderId,
                data: {
                    workorder_status: newStatus,
                    notes: updatedNotes || undefined,
                },
            },
            {
                onSuccess: () => {
                    toast.success(`Work order status updated to ${newStatus.replace("_", " ").toLowerCase()}`);
                    onStatusChange?.();
                },
                onError: (error) => {
                    console.error("Failed to update work order status:", error);
                    toast.error("Failed to update status");
                },
            }
        );
    };

    const handleRelease = () => {
        updateStatus("IN_PROGRESS", "RELEASED");
    };

    const handleHold = () => {
        if (!holdReason) {
            toast.error("Please select a hold reason");
            return;
        }

        const reasonLabel = HOLD_REASONS.find((r) => r.value === holdReason)?.label || holdReason;
        const holdNote = holdDetails
            ? `HOLD: ${reasonLabel} - ${holdDetails}`
            : `HOLD: ${reasonLabel}`;

        updateStatus("ON_HOLD", holdNote);
        setHoldDialogOpen(false);
        setHoldReason("");
        setHoldDetails("");
    };

    const handleResume = () => {
        updateStatus("IN_PROGRESS", "RESUMED");
    };

    const handleCancel = () => {
        updateStatus("CANCELLED", "CANCELLED");
        setCancelDialogOpen(false);
    };

    // Determine available actions based on current status
    const canRelease = currentStatus === "PENDING";
    const canHold = currentStatus === "IN_PROGRESS";
    const canResume = currentStatus === "ON_HOLD";
    const canCancel = currentStatus !== "COMPLETED" && currentStatus !== "CANCELLED";
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
                    onClick={handleRelease}
                    disabled={updateWorkOrder.isPending}
                >
                    <PlayCircle className="h-4 w-4 mr-2" />
                    Release
                </Button>
            )}

            {/* Hold Button */}
            {canHold && (
                <Dialog open={holdDialogOpen} onOpenChange={setHoldDialogOpen}>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setHoldDialogOpen(true)}
                        disabled={updateWorkOrder.isPending}
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
                                    onValueChange={(value) => setHoldReason(value as HoldReasonValue)}
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
                            {holdReason === "other" && (
                                <div className="space-y-2">
                                    <Label htmlFor="hold-details">Details</Label>
                                    <Textarea
                                        id="hold-details"
                                        placeholder="Provide details about the hold reason..."
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
                                disabled={!holdReason || updateWorkOrder.isPending}
                            >
                                Confirm Hold
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            )}

            {/* Resume Button */}
            {canResume && (
                <Button
                    variant="default"
                    size="sm"
                    onClick={handleResume}
                    disabled={updateWorkOrder.isPending}
                >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Resume
                </Button>
            )}

            {/* Cancel Button */}
            {canCancel && (
                <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
                    <AlertDialogTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            disabled={updateWorkOrder.isPending}
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
                                All associated parts will need to be reassigned to a new work order.
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
