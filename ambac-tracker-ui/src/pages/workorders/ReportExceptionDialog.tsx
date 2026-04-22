import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { CircleAlert } from "lucide-react";
import type { ExceptionItem, ExceptionSeverity } from "./mockData";

export type ReportExceptionPayload = Omit<ExceptionItem, "id" | "opened_at" | "closed_at" | "state">;

type Props = {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    /** If provided, the dialog pre-scopes to this WO and hides the impacted-WO field */
    scopedWorkOrderId?: string;
    scopedWorkOrderErpId?: string;
    onSubmit: (payload: ReportExceptionPayload) => void;
};

export function ReportExceptionDialog({
    open,
    onOpenChange,
    scopedWorkOrderId,
    scopedWorkOrderErpId,
    onSubmit,
}: Props) {
    const [kind, setKind] = useState<ExceptionItem["kind"]>("DOWNTIME");
    const [severity, setSeverity] = useState<ExceptionSeverity>("MEDIUM");
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [impactedErpIds, setImpactedErpIds] = useState("");

    useEffect(() => {
        if (!open) return;
        setKind("DOWNTIME");
        setSeverity("MEDIUM");
        setTitle("");
        setDescription("");
        setImpactedErpIds(scopedWorkOrderErpId ?? "");
    }, [open, scopedWorkOrderErpId]);

    const canSubmit = title.trim().length > 0 && description.trim().length > 0;

    function submit() {
        onSubmit({
            kind,
            severity,
            title: title.trim(),
            description: description.trim(),
            work_order_ids: scopedWorkOrderId
                ? [scopedWorkOrderId]
                : impactedErpIds
                      .split(/[,\s]+/)
                      .map((s) => s.trim())
                      .filter(Boolean),
            reported_by: "me",
            source_ref: "client-draft",
        });
        onOpenChange(false);
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <CircleAlert className="h-4 w-4" />
                        Report exception
                    </DialogTitle>
                    <DialogDescription>
                        Records an event that blocks or risks production. Routes to the right
                        aggregate by type — Downtime events, Quarantine dispositions, or CAPAs.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                            <Label>Type</Label>
                            <Select value={kind} onValueChange={(v) => setKind(v as ExceptionItem["kind"])}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="DOWNTIME">Downtime (equipment / resource)</SelectItem>
                                    <SelectItem value="QUARANTINE">Quarantine (quality hold)</SelectItem>
                                    <SelectItem value="CAPA">CAPA (corrective action)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <Label>Severity</Label>
                            <Select value={severity} onValueChange={(v) => setSeverity(v as ExceptionSeverity)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="LOW">Low</SelectItem>
                                    <SelectItem value="MEDIUM">Medium</SelectItem>
                                    <SelectItem value="HIGH">High</SelectItem>
                                    <SelectItem value="CRITICAL">Critical</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-1">
                        <Label htmlFor="exc-title">Title</Label>
                        <Input
                            id="exc-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder={
                                kind === "DOWNTIME"
                                    ? "e.g. Mill-03 spindle runout OOS"
                                    : kind === "QUARANTINE"
                                      ? "e.g. Bearing runout OOS at Final QC"
                                      : "e.g. Supplier delivery delay — backup vendor eval"
                            }
                        />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="exc-desc">Description</Label>
                        <Textarea
                            id="exc-desc"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="min-h-[80px]"
                        />
                    </div>

                    {scopedWorkOrderErpId ? (
                        <div className="rounded-md border bg-muted/30 p-2 text-xs text-muted-foreground">
                            Impacts <span className="font-mono">{scopedWorkOrderErpId}</span>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            <Label htmlFor="exc-wos">Impacted WOs</Label>
                            <Input
                                id="exc-wos"
                                value={impactedErpIds}
                                onChange={(e) => setImpactedErpIds(e.target.value)}
                                placeholder="WO-2026-0142, WO-2026-0143"
                                className="font-mono"
                            />
                            <p className="text-xs text-muted-foreground">
                                Comma-separated ERP IDs. Leave blank if not yet linked to a WO.
                            </p>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        Report exception
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
