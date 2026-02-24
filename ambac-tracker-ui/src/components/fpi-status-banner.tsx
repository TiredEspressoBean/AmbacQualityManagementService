import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertTriangle, Lock, CheckCircle } from "lucide-react";
import { useFpiCheckStatus, useFpiGetOrCreate, useFpiPass, useFpiFail, useFpiWaive } from "@/hooks/useFpiRecords";
import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

type FpiStatusBannerProps = {
    workOrderId: string;
    stepId: string;
    stepName?: string;
    /** Called when FPI status changes (e.g., after pass/fail/waive) */
    onStatusChange?: () => void;
    /** Show compact version */
    compact?: boolean;
};

export function FpiStatusBanner({
    workOrderId,
    stepId,
    stepName,
    onStatusChange,
    compact = false
}: FpiStatusBannerProps) {
    const [showWaiveDialog, setShowWaiveDialog] = useState(false);
    const [waiveReason, setWaiveReason] = useState("");

    const { data: fpiStatus, isLoading, refetch } = useFpiCheckStatus(workOrderId, stepId);
    const getOrCreateMutation = useFpiGetOrCreate();
    const passMutation = useFpiPass();
    const failMutation = useFpiFail();
    const waiveMutation = useFpiWaive();

    const handleStatusChange = () => {
        refetch();
        onStatusChange?.();
    };

    if (isLoading) {
        return null;
    }

    // No FPI required for this step
    if (!fpiStatus?.requires_fpi) {
        return null;
    }

    // FPI is satisfied (passed or waived)
    if (fpiStatus.satisfied) {
        if (compact) return null;

        return (
            <div className="rounded-lg p-3 border bg-green-500/10 border-green-500/50">
                <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-green-600" />
                    <div className="flex-1">
                        <p className="font-medium text-sm">First Piece Inspection Passed</p>
                        <p className="text-xs text-muted-foreground">
                            All parts can now proceed through this step.
                        </p>
                    </div>
                    <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
            </div>
        );
    }

    // FPI is pending or not yet created
    const isPending = fpiStatus.has_pending;

    const handleCreateFpi = async () => {
        try {
            await getOrCreateMutation.mutateAsync({
                work_order: workOrderId,
                step: stepId
            });
            toast.success("FPI record created");
            handleStatusChange();
        } catch (error) {
            toast.error("Failed to create FPI record");
        }
    };

    const handlePass = async () => {
        if (!fpiStatus.pending_fpi_id) return;
        try {
            await passMutation.mutateAsync({ id: fpiStatus.pending_fpi_id });
            toast.success("FPI passed - parts can now proceed");
            handleStatusChange();
        } catch (error) {
            toast.error("Failed to pass FPI");
        }
    };

    const handleFail = async () => {
        if (!fpiStatus.pending_fpi_id) return;
        try {
            await failMutation.mutateAsync({ id: fpiStatus.pending_fpi_id });
            toast.error("FPI failed - setup correction required");
            handleStatusChange();
        } catch (error) {
            toast.error("Failed to record FPI failure");
        }
    };

    const handleWaive = async () => {
        if (!fpiStatus.pending_fpi_id || waiveReason.length < 10) return;
        try {
            await waiveMutation.mutateAsync({
                id: fpiStatus.pending_fpi_id,
                reason: waiveReason
            });
            toast.success("FPI requirement waived");
            setShowWaiveDialog(false);
            setWaiveReason("");
            handleStatusChange();
        } catch (error) {
            toast.error("Failed to waive FPI");
        }
    };

    return (
        <>
            <div className="rounded-lg p-3 border bg-amber-500/10 border-amber-500/50">
                <div className="flex items-center gap-3">
                    <Lock className="h-5 w-5 text-amber-600" />
                    <div className="flex-1">
                        <p className="font-medium text-sm">
                            First Piece Inspection Required
                            {stepName && <span className="text-muted-foreground"> at {stepName}</span>}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {isPending
                                ? "Complete the FPI inspection before other parts can proceed."
                                : "Start FPI to unlock other parts at this step."}
                        </p>
                    </div>

                    {!compact && (
                        <div className="flex items-center gap-2">
                            {!isPending ? (
                                <Button
                                    size="sm"
                                    onClick={handleCreateFpi}
                                    disabled={getOrCreateMutation.isPending}
                                >
                                    Start FPI
                                </Button>
                            ) : (
                                <>
                                    <Button
                                        size="sm"
                                        variant="default"
                                        onClick={handlePass}
                                        disabled={passMutation.isPending}
                                        className="bg-green-600 hover:bg-green-700"
                                    >
                                        <CheckCircle className="h-4 w-4 mr-1" />
                                        Pass
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={handleFail}
                                        disabled={failMutation.isPending}
                                    >
                                        <AlertTriangle className="h-4 w-4 mr-1" />
                                        Fail
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => setShowWaiveDialog(true)}
                                    >
                                        Waive
                                    </Button>
                                </>
                            )}
                        </div>
                    )}

                    {compact && isPending && (
                        <Badge variant="secondary">
                            FPI Pending
                        </Badge>
                    )}
                </div>
            </div>

            {/* Waive Dialog */}
            <Dialog open={showWaiveDialog} onOpenChange={setShowWaiveDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Waive FPI Requirement</DialogTitle>
                        <DialogDescription>
                            Waiving FPI allows parts to proceed without first piece inspection.
                            This should only be done with proper authorization.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div>
                            <label className="text-sm font-medium">
                                Reason for Waiving (minimum 10 characters)
                            </label>
                            <Textarea
                                value={waiveReason}
                                onChange={(e) => setWaiveReason(e.target.value)}
                                placeholder="Enter justification for waiving FPI..."
                                className="mt-1"
                                rows={3}
                            />
                            {waiveReason.length > 0 && waiveReason.length < 10 && (
                                <p className="text-xs text-red-500 mt-1">
                                    {10 - waiveReason.length} more characters required
                                </p>
                            )}
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowWaiveDialog(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleWaive}
                            disabled={waiveReason.length < 10 || waiveMutation.isPending}
                        >
                            Waive FPI
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
