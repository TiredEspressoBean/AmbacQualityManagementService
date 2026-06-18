import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertTriangle, Lock, CheckCircle, Clock, PenLine } from "lucide-react";
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

/**
 * FPI banner — state-aware. It mirrors the real first-piece flow:
 *   1. Required (no record yet)      → Start FPI (operator initiates).
 *   2. In progress (first piece not  → "complete the inspection below"; the run
 *      done)                            is held, no buy-off possible yet.
 *   3. First piece complete          → an approved person signs off (pass/fail/
 *                                        waive); everyone else sees "awaiting
 *                                        buy-off".
 *   4. Satisfied (passed/waived)     → green, run released.
 *
 * Sign-off is gated server-side on `sign_off_fpi`; `can_sign_off` from
 * check-status decides whether this user sees the buy-off actions.
 */
export function FpiStatusBanner({
    workOrderId,
    stepId,
    stepName,
    onStatusChange,
    compact = false,
}: FpiStatusBannerProps) {
    const [signOffOpen, setSignOffOpen] = useState(false);
    const [failOpen, setFailOpen] = useState(false);
    const [waiveOpen, setWaiveOpen] = useState(false);
    const [notes, setNotes] = useState("");
    const [waiveReason, setWaiveReason] = useState("");

    const { data: fpiStatus, isLoading, refetch } = useFpiCheckStatus(workOrderId, stepId);
    const getOrCreateMutation = useFpiGetOrCreate();
    const passMutation = useFpiPass();
    const failMutation = useFpiFail();
    const waiveMutation = useFpiWaive();

    const afterChange = () => {
        refetch();
        onStatusChange?.();
    };

    if (isLoading) return null;
    if (!fpiStatus?.requires_fpi) return null;

    // ---- Satisfied: run released --------------------------------------------
    if (fpiStatus.satisfied) {
        if (compact) return null;
        return (
            <div className="rounded-lg p-3 border bg-green-500/10 border-green-500/50">
                <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-green-600" />
                    <div className="flex-1">
                        <p className="font-medium text-sm">First Piece Inspection signed off</p>
                        <p className="text-xs text-muted-foreground">
                            Setup verified — all parts can proceed through this step.
                        </p>
                    </div>
                    <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
            </div>
        );
    }

    const pendingId = fpiStatus.pending_fpi_id;
    const partLabel = fpiStatus.designated_part_label;
    const firstPiece = partLabel ? `first piece ${partLabel}` : "first piece";

    const handleCreateFpi = async () => {
        try {
            await getOrCreateMutation.mutateAsync({ work_order: workOrderId, step: stepId });
            toast.success("FPI started — first piece designated");
            afterChange();
        } catch {
            toast.error("Failed to start FPI");
        }
    };

    const handleSignOff = async () => {
        if (!pendingId) return;
        try {
            await passMutation.mutateAsync({ id: pendingId, notes });
            toast.success("FPI signed off — parts can now proceed");
            setSignOffOpen(false);
            setNotes("");
            afterChange();
        } catch (e: unknown) {
            toast.error(extractDetail(e) ?? "Failed to sign off FPI");
        }
    };

    const handleFail = async () => {
        if (!pendingId) return;
        try {
            await failMutation.mutateAsync({ id: pendingId, notes });
            toast.error("FPI failed — correct the setup and re-run the first piece");
            setFailOpen(false);
            setNotes("");
            afterChange();
        } catch (e: unknown) {
            toast.error(extractDetail(e) ?? "Failed to record FPI failure");
        }
    };

    const handleWaive = async () => {
        if (!pendingId || waiveReason.length < 10) return;
        try {
            await waiveMutation.mutateAsync({ id: pendingId, reason: waiveReason });
            toast.success("FPI requirement waived");
            setWaiveOpen(false);
            setWaiveReason("");
            afterChange();
        } catch (e: unknown) {
            toast.error(extractDetail(e) ?? "Failed to waive FPI");
        }
    };

    const isPending = fpiStatus.has_pending;
    const ready = fpiStatus.first_piece_ready;
    const canSignOff = fpiStatus.can_sign_off;

    // Pick the banner's shape from the flow state.
    let icon = <Lock className="h-5 w-5 text-amber-600" />;
    let title = "First Piece Inspection Required";
    let detail = "Start FPI to designate the first piece and hold the run until buy-off.";
    let actions: React.ReactNode = null;

    if (!isPending) {
        actions = !compact ? (
            <Button size="sm" onClick={handleCreateFpi} disabled={getOrCreateMutation.isPending}>
                Start FPI
            </Button>
        ) : <Badge variant="secondary">FPI required</Badge>;
    } else if (!ready) {
        // First piece designated but its inspection isn't finished yet.
        icon = <Clock className="h-5 w-5 text-amber-600" />;
        title = "First Piece Inspection in progress";
        detail = `Complete the ${firstPiece} inspection below — the run is held until it's bought off.`;
        actions = compact ? <Badge variant="secondary">FPI in progress</Badge> : null;
    } else if (canSignOff) {
        // First piece complete; this user may buy off.
        icon = <PenLine className="h-5 w-5 text-blue-600" />;
        title = "First piece complete — ready for buy-off";
        detail = `Review the ${firstPiece} results below, then sign off to release the run.`;
        actions = !compact ? (
            <div className="flex items-center gap-2">
                <Button
                    size="sm"
                    onClick={() => setSignOffOpen(true)}
                    className="bg-green-600 hover:bg-green-700"
                >
                    <PenLine className="h-4 w-4 mr-1" />
                    Sign off &amp; pass
                </Button>
                <Button size="sm" variant="destructive" onClick={() => setFailOpen(true)}>
                    <AlertTriangle className="h-4 w-4 mr-1" />
                    Fail
                </Button>
                <Button size="sm" variant="outline" onClick={() => setWaiveOpen(true)}>
                    Waive
                </Button>
            </div>
        ) : <Badge variant="secondary">Awaiting buy-off</Badge>;
    } else {
        // First piece complete; this user is not an approver.
        icon = <Clock className="h-5 w-5 text-amber-600" />;
        title = "First piece complete — awaiting buy-off";
        detail = `${partLabel ?? "The first piece"} is ready for an authorized sign-off before the run can proceed.`;
        actions = compact ? <Badge variant="secondary">Awaiting buy-off</Badge> : null;
    }

    return (
        <>
            <div className="rounded-lg p-3 border bg-amber-500/10 border-amber-500/50">
                <div className="flex items-center gap-3">
                    {icon}
                    <div className="flex-1">
                        <p className="font-medium text-sm">
                            {title}
                            {stepName && <span className="text-muted-foreground"> at {stepName}</span>}
                        </p>
                        <p className="text-xs text-muted-foreground">{detail}</p>
                    </div>
                    {actions}
                </div>
            </div>

            {/* Sign-off (pass) — the buy-off attestation */}
            <Dialog open={signOffOpen} onOpenChange={setSignOffOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Sign off First Piece Inspection</DialogTitle>
                        <DialogDescription>
                            By signing off you attest that the setup is correct and the first piece
                            {partLabel ? ` (${partLabel})` : ""} conforms. This is recorded against
                            your name and releases the run.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Notes (optional)</label>
                        <Textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Inspection notes / gauges used / observations…"
                            rows={3}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSignOffOpen(false)}>Cancel</Button>
                        <Button
                            onClick={handleSignOff}
                            disabled={passMutation.isPending}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            Confirm sign-off
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Fail — records the failure reason; first piece must be re-run */}
            <Dialog open={failOpen} onOpenChange={setFailOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Fail First Piece Inspection</DialogTitle>
                        <DialogDescription>
                            The setup did not pass. The run stays held; correct the setup and re-run
                            a new first piece for re-inspection.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Reason / findings</label>
                        <Textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="What was out of spec / what needs correcting…"
                            rows={3}
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setFailOpen(false)}>Cancel</Button>
                        <Button variant="destructive" onClick={handleFail} disabled={failMutation.isPending}>
                            Record failure
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Waive — authorized skip */}
            <Dialog open={waiveOpen} onOpenChange={setWaiveOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Waive FPI Requirement</DialogTitle>
                        <DialogDescription>
                            Waiving lets parts proceed without first-piece sign-off. Use only with
                            proper authorization.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Reason for waiving (min 10 characters)</label>
                        <Textarea
                            value={waiveReason}
                            onChange={(e) => setWaiveReason(e.target.value)}
                            placeholder="Justification for waiving FPI…"
                            rows={3}
                        />
                        {waiveReason.length > 0 && waiveReason.length < 10 && (
                            <p className="text-xs text-red-500">
                                {10 - waiveReason.length} more characters required
                            </p>
                        )}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setWaiveOpen(false)}>Cancel</Button>
                        <Button onClick={handleWaive} disabled={waiveReason.length < 10 || waiveMutation.isPending}>
                            Waive FPI
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

/** Pull a human message out of a zodios/axios error if present. */
function extractDetail(e: unknown): string | undefined {
    const data = (e as { response?: { data?: { detail?: string; blockers?: string[] } } })?.response?.data;
    if (!data) return undefined;
    if (data.blockers?.length) return `${data.detail ?? "Incomplete"} — ${data.blockers.join("; ")}`;
    return data.detail;
}
