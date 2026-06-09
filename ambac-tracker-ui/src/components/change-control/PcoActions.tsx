import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Hammer, Ban, FileEdit } from "lucide-react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import { ReasonPromptDialog } from "./ReasonPromptDialog";
import {
    useAuthorPco,
    useMarkPcoApproved,
    useImplementPco,
    useCancelPco,
    type MigrationDisposition,
} from "@/hooks/useChangeControlActions";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAffectedWorkorders, type AffectedWorkorderRow } from "@/hooks/useAffectedWorkorders";

type Props = {
    pcoId: string;
    status: string;
    implementationPlan?: string;
    effectiveDate?: string | null;
};

export function PcoActions({ pcoId, status, implementationPlan, effectiveDate }: Props) {
    const [authorOpen, setAuthorOpen] = useState(false);
    const [implementOpen, setImplementOpen] = useState(false);
    const [cancelOpen, setCancelOpen] = useState(false);

    const author = useAuthorPco();
    const markApproved = useMarkPcoApproved();
    const implement = useImplementPco();
    const cancel = useCancelPco();
    const { has } = usePermissionSet();

    const canChange = has("change_processchangeorder");
    const canAuthor = canChange && status === "DRAFT";
    const canMarkApproved = canChange && (status === "DRAFT" || status === "UNDER_APPROVAL");
    const canImplement = canChange && status === "APPROVED";
    const canCancel = canChange && (status === "DRAFT" || status === "UNDER_APPROVAL" || status === "APPROVED");

    if (!canAuthor && !canMarkApproved && !canImplement && !canCancel) return null;

    return (
        <div className="flex flex-wrap gap-2">
            {canAuthor && (
                <Button size="sm" variant="outline" onClick={() => setAuthorOpen(true)}>
                    <FileEdit className="h-4 w-4 mr-2" /> Edit plan
                </Button>
            )}
            {canMarkApproved && (
                <Button
                    size="sm"
                    onClick={async () => {
                        try {
                            await markApproved.mutateAsync({ id: pcoId });
                            toast.success("PCO approved");
                        } catch (e) {
                            toast.error("Approve failed", { description: e instanceof Error ? e.message : undefined });
                        }
                    }}
                    disabled={markApproved.isPending}
                >
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    {markApproved.isPending ? "…" : "Mark approved"}
                </Button>
            )}
            {canImplement && (
                <Button size="sm" onClick={() => setImplementOpen(true)}>
                    <Hammer className="h-4 w-4 mr-2" /> Implement
                </Button>
            )}
            {canCancel && (
                <Button size="sm" variant="outline" onClick={() => setCancelOpen(true)}>
                    <Ban className="h-4 w-4 mr-2" /> Cancel
                </Button>
            )}

            <AuthorPlanDialog
                open={authorOpen}
                onOpenChange={setAuthorOpen}
                initialPlan={implementationPlan ?? ""}
                initialEffective={effectiveDate ?? ""}
                pending={author.isPending}
                onSubmit={async (plan, effective) => {
                    try {
                        await author.mutateAsync({
                            id: pcoId,
                            implementation_plan: plan,
                            effective_date: effective || null,
                        });
                        toast.success("Implementation plan saved");
                        setAuthorOpen(false);
                    } catch (e) {
                        toast.error("Save failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />

            <ImplementDialog
                open={implementOpen}
                onOpenChange={setImplementOpen}
                pcoId={pcoId}
                pending={implement.isPending}
                onSubmit={async (disposition, reason, selectedIds) => {
                    try {
                        await implement.mutateAsync({
                            id: pcoId,
                            migration_disposition: disposition,
                            migration_reason: reason,
                            selected_workorder_ids: disposition === "MIGRATE_SELECTED" ? selectedIds : undefined,
                        });
                        toast.success("PCO implemented");
                        setImplementOpen(false);
                    } catch (e) {
                        toast.error("Implement failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />

            <ReasonPromptDialog
                open={cancelOpen}
                onOpenChange={setCancelOpen}
                title="Cancel PCO"
                description="The PCO will be marked CANCELLED. Leave an optional note for the audit log."
                placeholder="Optional reason"
                confirmLabel="Cancel PCO"
                required={false}
                pending={cancel.isPending}
                onSubmit={async (reason) => {
                    try {
                        await cancel.mutateAsync({ id: pcoId, reason });
                        toast.success("PCO cancelled");
                        setCancelOpen(false);
                    } catch (e) {
                        toast.error("Cancel failed", { description: e instanceof Error ? e.message : undefined });
                    }
                }}
            />
        </div>
    );
}

function AuthorPlanDialog({
    open, onOpenChange, initialPlan, initialEffective, pending, onSubmit,
}: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    initialPlan: string;
    initialEffective: string;
    pending: boolean;
    onSubmit: (plan: string, effective: string) => void;
}) {
    const [plan, setPlan] = useState(initialPlan);
    const [effective, setEffective] = useState(initialEffective);
    useEffect(() => {
        if (open) {
            setPlan(initialPlan);
            setEffective(initialEffective);
        }
    }, [open, initialPlan, initialEffective]);
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Edit implementation plan</DialogTitle>
                    <DialogDescription>
                        Describe how the change will be rolled out and pick an effective date.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2">
                    <div>
                        <Label htmlFor="pco-plan">Implementation plan</Label>
                        <Textarea id="pco-plan" rows={5} value={plan} onChange={(e) => setPlan(e.target.value)} />
                    </div>
                    <div>
                        <Label htmlFor="pco-effective">Effective date</Label>
                        <Input id="pco-effective" type="date" value={effective} onChange={(e) => setEffective(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
                    <Button disabled={pending} onClick={() => onSubmit(plan, effective)}>
                        {pending ? "Saving…" : "Save plan"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function ImplementDialog({
    open, onOpenChange, pcoId, pending, onSubmit,
}: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    pcoId: string;
    pending: boolean;
    onSubmit: (disposition: MigrationDisposition, reason: string, selectedIds: string[]) => void;
}) {
    const [disposition, setDisposition] = useState<MigrationDisposition>("KEEP_ALL");
    const [reason, setReason] = useState("");
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    useEffect(() => {
        if (open) {
            setDisposition("KEEP_ALL");
            setReason("");
            setSelectedIds(new Set());
        }
    }, [open]);

    const needsPicker = disposition === "MIGRATE_SELECTED";
    const { data: affected, isLoading } = useAffectedWorkorders(pcoId, open && needsPicker);

    const toggleOne = (id: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };
    const toggleAll = (checked: boolean) => {
        if (!affected) return;
        setSelectedIds(checked ? new Set(affected.map((r) => r.wo_id)) : new Set());
    };

    const canSubmit = !needsPicker || selectedIds.size > 0;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                className={
                    needsPicker
                        ? "sm:max-w-5xl max-h-[90vh] overflow-y-auto"
                        : "sm:max-w-md max-h-[90vh] overflow-y-auto"
                }
            >
                <DialogHeader>
                    <DialogTitle>Implement PCO</DialogTitle>
                    <DialogDescription>
                        Choose how in-flight work orders are affected. A PCN is emitted on success.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2">
                    <div>
                        <Label htmlFor="pco-disposition">Migration disposition</Label>
                        <Select value={disposition} onValueChange={(v) => setDisposition(v as MigrationDisposition)}>
                            <SelectTrigger id="pco-disposition"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="KEEP_ALL">Keep all in-flight WOs on the old version</SelectItem>
                                <SelectItem value="MIGRATE_ALL">Migrate all in-flight WOs to the new version</SelectItem>
                                <SelectItem value="MIGRATE_SELECTED">Migrate selected WOs only</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {needsPicker && (
                        <WorkorderPicker
                            rows={affected}
                            isLoading={isLoading}
                            selectedIds={selectedIds}
                            onToggleOne={toggleOne}
                            onToggleAll={toggleAll}
                        />
                    )}

                    <div>
                        <Label htmlFor="pco-reason">Migration reason</Label>
                        <Textarea id="pco-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Optional context for the audit log" />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
                    <Button
                        disabled={pending || !canSubmit}
                        onClick={() => onSubmit(disposition, reason, Array.from(selectedIds))}
                    >
                        {pending ? "Implementing…" : needsPicker ? `Implement (${selectedIds.size})` : "Implement"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function WorkorderPicker({
    rows, isLoading, selectedIds, onToggleOne, onToggleAll,
}: {
    rows: AffectedWorkorderRow[] | undefined;
    isLoading: boolean;
    selectedIds: Set<string>;
    onToggleOne: (id: string) => void;
    onToggleAll: (checked: boolean) => void;
}) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading affected work orders…
            </div>
        );
    }
    if (!rows || rows.length === 0) {
        return (
            <div className="py-4 text-sm text-muted-foreground italic">
                No in-flight work orders on the target process.
            </div>
        );
    }
    const allChecked = rows.length > 0 && rows.every((r) => selectedIds.has(r.wo_id));
    return (
        <div className="border rounded-md overflow-hidden">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-10">
                            <Checkbox
                                checked={allChecked}
                                onCheckedChange={(v) => onToggleAll(!!v)}
                                aria-label="Select all"
                            />
                        </TableHead>
                        <TableHead>Work Order</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">In flight</TableHead>
                        <TableHead className="text-right">Affected</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {rows.map((r) => {
                        const checked = selectedIds.has(r.wo_id);
                        return (
                            <TableRow
                                key={r.wo_id}
                                className="cursor-pointer"
                                onClick={() => onToggleOne(r.wo_id)}
                            >
                                <TableCell onClick={(e) => e.stopPropagation()}>
                                    <Checkbox
                                        checked={checked}
                                        onCheckedChange={() => onToggleOne(r.wo_id)}
                                        aria-label={`Select ${r.erp_id}`}
                                    />
                                </TableCell>
                                <TableCell className="font-mono text-xs">{r.erp_id}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="text-[10px]">{r.status}</Badge>
                                </TableCell>
                                <TableCell className="text-right tabular-nums">{r.quantity}</TableCell>
                                <TableCell className="text-right tabular-nums">{r.total_parts}</TableCell>
                                <TableCell className="text-right tabular-nums">
                                    {r.affected_parts > 0 ? (
                                        <span className="text-amber-600 dark:text-amber-400 font-medium">{r.affected_parts}</span>
                                    ) : (
                                        <span className="text-muted-foreground">0</span>
                                    )}
                                </TableCell>
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
}
