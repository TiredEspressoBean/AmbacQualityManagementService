import { useState } from "react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useSubmitProcessChangeRequest } from "@/hooks/useSubmitProcessChangeRequest";
import { toast } from "sonner";

type Priority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    pcr: {
        id: string;
        artifact_number?: string;
        title?: string;
        proposed_change?: string;
        justification?: string;
        risk_analysis?: string;
        priority?: string;
        customer_notification_required?: boolean;
        is_temporary?: boolean;
        temporary_until?: string | null;
        customer_agreement?: string;
        extends_request_number?: string | null;
    };
    onSubmitted?: () => void;
};

export function SubmitPcrDialog({ open, onOpenChange, pcr, onSubmitted }: Props) {
    const [title, setTitle] = useState(pcr.title ?? "");
    const [proposedChange, setProposedChange] = useState(pcr.proposed_change ?? "");
    const [justification, setJustification] = useState(pcr.justification ?? "");
    const [riskAnalysis, setRiskAnalysis] = useState(pcr.risk_analysis ?? "");
    const [priority, setPriority] = useState<Priority>((pcr.priority as Priority) ?? "NORMAL");
    const [customerNotify, setCustomerNotify] = useState(pcr.customer_notification_required ?? false);
    // A temporary change (deviation) applies only to the work orders named when it is
    // implemented, and ends on this date unless another PCR extends it.
    const isExtension = !!pcr.extends_request_number;
    const [isTemporary, setIsTemporary] = useState(pcr.is_temporary ?? false);
    const [temporaryUntil, setTemporaryUntil] = useState(pcr.temporary_until ?? "");
    const [customerAgreement, setCustomerAgreement] = useState(pcr.customer_agreement ?? "");

    const submit = useSubmitProcessChangeRequest();

    const handleSubmit = async () => {
        if (!title.trim()) {
            toast.error("Title is required");
            return;
        }
        if (!proposedChange.trim()) {
            toast.error("Describe the proposed change");
            return;
        }
        if (!justification.trim()) {
            toast.error("Say why the change is needed");
            return;
        }
        if (!riskAnalysis.trim()) {
            toast.error("Describe the risks and how they're handled");
            return;
        }
        if (isTemporary && !isExtension && !temporaryUntil) {
            toast.error("A temporary change needs the date it ends");
            return;
        }
        try {
            await submit.mutateAsync({
                pcrId: pcr.id,
                patch: {
                    title,
                    proposed_change: proposedChange,
                    justification,
                    risk_analysis: riskAnalysis,
                    priority,
                    customer_notification_required: customerNotify,
                    customer_agreement: customerAgreement,
                    // An extension's date is fixed when it is raised.
                    ...(isExtension ? {} : {
                        is_temporary: isTemporary,
                        temporary_until: isTemporary ? temporaryUntil : null,
                    }),
                },
            });
            toast.success(`${pcr.artifact_number ?? "PCR"} submitted for approval`);
            onOpenChange(false);
            onSubmitted?.();
        } catch {
            // The global mutation handler shows the server's reason (e.g. a draft that
            // changes nothing); the dialog stays open to correct and retry.
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Submit {pcr.artifact_number ?? "PCR"} for approval</DialogTitle>
                    <DialogDescription>
                        The diff between this draft and the approved baseline will be
                        captured automatically and attached to the request.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div>
                        <Label htmlFor="pcr-title">Title <span className="text-destructive">*</span></Label>
                        <Input
                            id="pcr-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Short summary of the change"
                        />
                    </div>

                    <div>
                        <Label htmlFor="pcr-change">Proposed change <span className="text-destructive">*</span></Label>
                        <Textarea
                            id="pcr-change"
                            value={proposedChange}
                            onChange={(e) => setProposedChange(e.target.value)}
                            placeholder="What is changing, in narrative form"
                            rows={4}
                        />
                    </div>

                    <div>
                        <Label htmlFor="pcr-justification">Justification <span className="text-destructive">*</span></Label>
                        <Textarea
                            id="pcr-justification"
                            value={justification}
                            onChange={(e) => setJustification(e.target.value)}
                            placeholder="Why this change is needed (defects observed, customer request, etc.)"
                            rows={3}
                        />
                    </div>

                    <div>
                        <Label htmlFor="pcr-risk">Risk analysis <span className="text-destructive">*</span></Label>
                        <Textarea
                            id="pcr-risk"
                            value={riskAnalysis}
                            onChange={(e) => setRiskAnalysis(e.target.value)}
                            placeholder="Risks, mitigations, validation plan"
                            rows={3}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <Label htmlFor="pcr-priority">Priority</Label>
                            <Select value={priority} onValueChange={(v) => setPriority(v as Priority)}>
                                <SelectTrigger id="pcr-priority"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="LOW">Low</SelectItem>
                                    <SelectItem value="NORMAL">Normal</SelectItem>
                                    <SelectItem value="HIGH">High</SelectItem>
                                    <SelectItem value="CRITICAL">Critical</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-end gap-3 pb-1">
                            <Switch
                                id="pcr-customer"
                                checked={customerNotify}
                                onCheckedChange={setCustomerNotify}
                            />
                            <Label htmlFor="pcr-customer" className="text-sm">
                                Customer notification required
                            </Label>
                        </div>
                    </div>

                    {isExtension ? (
                        <p className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                            Extends temporary change <span className="font-medium">{pcr.extends_request_number}</span>
                            {pcr.temporary_until ? ` to ${pcr.temporary_until}` : ""}. No process edit.
                        </p>
                    ) : (
                        <div className="space-y-3 rounded-md border p-3">
                            <div className="flex items-center gap-3">
                                <Switch id="pcr-temporary" checked={isTemporary} onCheckedChange={setIsTemporary} />
                                <Label htmlFor="pcr-temporary" className="text-sm">Temporary change (deviation)</Label>
                            </div>
                            {isTemporary && (
                                <>
                                    <p className="text-xs text-muted-foreground">
                                        Applies only to the work orders you name when it is implemented. The current
                                        version stays in force for everything else. After the end date its work can't
                                        proceed until another change extends it, or the work order goes back.
                                    </p>
                                    <div>
                                        <Label htmlFor="pcr-temporary-until">Ends on</Label>
                                        <Input
                                            id="pcr-temporary-until"
                                            type="date"
                                            value={temporaryUntil}
                                            onChange={(e) => setTemporaryUntil(e.target.value)}
                                        />
                                    </div>
                                </>
                            )}
                        </div>
                    )}

                    {customerNotify && (
                        <div>
                            <Label htmlFor="pcr-customer-agreement">Customer agreement</Label>
                            <Textarea
                                id="pcr-customer-agreement"
                                value={customerAgreement}
                                onChange={(e) => setCustomerAgreement(e.target.value)}
                                placeholder="The customer's answer — who agreed, when, and their reference (or attach it to the request)"
                                rows={2}
                            />
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submit.isPending}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={submit.isPending}>
                        {submit.isPending ? "Submitting…" : "Submit for approval"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
