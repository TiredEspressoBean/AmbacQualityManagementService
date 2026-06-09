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
                },
            });
            toast.success(`${pcr.artifact_number ?? "PCR"} submitted for approval`);
            onOpenChange(false);
            onSubmitted?.();
        } catch (err) {
            toast.error("Submit failed", {
                description: err instanceof Error ? err.message : undefined,
            });
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
                        <Label htmlFor="pcr-justification">Justification</Label>
                        <Textarea
                            id="pcr-justification"
                            value={justification}
                            onChange={(e) => setJustification(e.target.value)}
                            placeholder="Why this change is needed (defects observed, customer request, etc.)"
                            rows={3}
                        />
                    </div>

                    <div>
                        <Label htmlFor="pcr-risk">Risk analysis</Label>
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
