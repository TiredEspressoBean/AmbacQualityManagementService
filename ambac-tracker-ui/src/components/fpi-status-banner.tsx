import { Badge } from "@/components/ui/badge";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertTriangle, Lock, CheckCircle, Clock, PenLine } from "lucide-react";
import { useFpiCheckStatus, useFpiGetOrCreate, useFpiVoidPass } from "@/hooks/useFpiRecords";
import { useState } from "react";
import { FpiSignOffDialog, type FpiVerdict } from "@/components/fpi-sign-off-dialog";
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
    /** The part at this station. Under a Per Shift / Per Equipment scope the first
     *  piece is for its context (today's shift, the machine it runs on). */
    partId?: string;
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
    partId,
    stepName,
    onStatusChange,
    compact = false,
}: FpiStatusBannerProps) {
    // Pass, fail and waive all go through the shared buy-off dialog, which carries
    // the step's password assurance, the co-sign switch when you signed the first
    // piece yourself, and the required fail reason. This banner's own dialogs had
    // none of the three.
    const [verdict, setVerdict] = useState<FpiVerdict | null>(null);
    const [voidOpen, setVoidOpen] = useState(false);
    const [voidReason, setVoidReason] = useState("");

    const { data: fpiStatus, isLoading, refetch } = useFpiCheckStatus(workOrderId, stepId, undefined, partId);
    const getOrCreateMutation = useFpiGetOrCreate();
    const voidMutation = useFpiVoidPass();
    const [restartOpen, setRestartOpen] = useState(false);

    const afterChange = () => {
        refetch();
        onStatusChange?.();
    };

    if (isLoading) return null;
    if (!fpiStatus?.requires_fpi) return null;

    // Who the first piece is for under the step's scope: "the 28 Oct shift", "CNC-1".
    const forContext = fpiStatus.context_label ? ` for ${fpiStatus.context_label}` : "";

    const handleCreateFpi = async () => {
        try {
            await getOrCreateMutation.mutateAsync({ work_order: workOrderId, step: stepId, part: partId });
            toast.success("FPI started — first piece designated");
            setRestartOpen(false);
            afterChange();
        } catch (e: unknown) {
            toast.error(apiErrorMessage(e) ?? "Failed to start FPI");
        }
    };

    // ---- Satisfied: run released --------------------------------------------
    if (fpiStatus.satisfied) {
        if (compact) return null;
        const waived = Boolean(fpiStatus.waived_fpi_id);
        const voidable = fpiStatus.can_sign_off ? fpiStatus.passed_fpi_id : null;
        const handleVoid = async () => {
            if (!voidable || !voidReason.trim()) return;
            try {
                await voidMutation.mutateAsync({ id: voidable, reason: voidReason.trim() });
                toast.success("Pass voided — the run holds until the first piece is re-inspected");
                setVoidOpen(false);
                setVoidReason("");
                afterChange();
            } catch (e: unknown) {
                toast.error(apiErrorMessage(e) ?? "Failed to void the pass");
            }
        };
        return (
            <div className="rounded-lg p-3 border bg-green-500/10 border-green-500/50">
                <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-green-600" />
                    <div className="flex-1">
                        <p className="font-medium text-sm">
                            {waived ? "First Piece Inspection waived" : "First Piece Inspection signed off"}{forContext}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {waived
                                ? "Released without a first-piece buy-off — parts can proceed through this step."
                                : "Setup verified — all parts can proceed through this step."}
                        </p>
                    </div>
                    {voidable && (
                        <Button size="sm" variant="ghost" onClick={() => setVoidOpen(true)}>
                            Void pass
                        </Button>
                    )}
                    {/* A waiver is corrected by a new first piece (a pass by Void pass). */}
                    {fpiStatus.can_restart && (
                        <Button size="sm" variant="ghost" onClick={() => setRestartOpen(true)}>
                            Start a new first piece
                        </Button>
                    )}
                    <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
                <Dialog open={restartOpen} onOpenChange={setRestartOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Start a new first piece</DialogTitle>
                            <DialogDescription>
                                The waiver stays on record, marked superseded. The run holds{forContext} until
                                the new first piece is passed or waived. Parts already past this step are not
                                pulled back.
                            </DialogDescription>
                        </DialogHeader>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setRestartOpen(false)}
                                disabled={getOrCreateMutation.isPending}>Cancel</Button>
                            <Button onClick={handleCreateFpi} disabled={getOrCreateMutation.isPending}>
                                {getOrCreateMutation.isPending ? "Starting…" : "Start a new first piece"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
                <Dialog open={voidOpen} onOpenChange={setVoidOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Void the first-piece pass</DialogTitle>
                            <DialogDescription>
                                The pass stays on record, marked voided with your reason. The step&rsquo;s
                                release is withdrawn and a new first-piece inspection opens: parts not yet
                                past this step wait until the piece is re-inspected. Parts already past it
                                are not pulled back.
                            </DialogDescription>
                        </DialogHeader>
                        <Textarea rows={3} value={voidReason} onChange={(e) => setVoidReason(e.target.value)}
                            placeholder="Why — e.g. bore read on the wrong gauge" aria-label="Reason" />
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setVoidOpen(false)} disabled={voidMutation.isPending}>Cancel</Button>
                            <Button variant="destructive" onClick={handleVoid}
                                disabled={!voidReason.trim() || voidMutation.isPending}>
                                {voidMutation.isPending ? "Voiding…" : "Void pass"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        );
    }

    const pendingId = fpiStatus.pending_fpi_id;
    const partLabel = fpiStatus.designated_part_label;
    const firstPiece = partLabel ? `first piece ${partLabel}` : "first piece";

    const isPending = fpiStatus.has_pending;
    const ready = fpiStatus.first_piece_ready;
    const canSignOff = fpiStatus.can_sign_off;

    // Pick the banner's shape from the flow state.
    let icon = <Lock className="h-5 w-5 text-amber-600" />;
    let title = `First Piece Inspection Required${forContext}`;
    let detail = "Start FPI to designate the first piece and hold the run until buy-off.";
    let actions: React.ReactNode = null;

    if (fpiStatus.context_known === false) {
        // Per Equipment, and nothing says which machine this part runs on.
        title = "First Piece Inspection Required — machine not recorded";
        detail = "This step needs a first piece per machine. Record the machine this part runs on, then start the FPI.";
        actions = compact ? <Badge variant="secondary">FPI required</Badge> : null;
    } else if (!isPending) {
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
                    onClick={() => setVerdict("PASS")}
                    className="bg-green-600 hover:bg-green-700"
                >
                    <PenLine className="h-4 w-4 mr-1" />
                    Sign off &amp; pass
                </Button>
                <Button size="sm" variant="destructive" onClick={() => setVerdict("FAIL")}>
                    <AlertTriangle className="h-4 w-4 mr-1" />
                    Fail
                </Button>
                <Button size="sm" variant="outline" onClick={() => setVerdict("WAIVE")}>
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

            {verdict && pendingId && (
                <FpiSignOffDialog
                    key={verdict}
                    open
                    onOpenChange={(v) => !v && setVerdict(null)}
                    fpiId={pendingId}
                    canSignOff={canSignOff}
                    partLabel={partLabel ?? null}
                    verdict={verdict}
                    onSigned={() => { setVerdict(null); afterChange(); }}
                />
            )}
        </>
    );
}

