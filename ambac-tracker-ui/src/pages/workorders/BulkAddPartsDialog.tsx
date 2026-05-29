import { useEffect, useMemo, useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { useRetrieveProcessWithSteps } from "@/hooks/useRetrieveProcessWithSteps";
import { useRetrievePartType } from "@/hooks/useRetrievePartType";
import { useBulkAddPartsToWorkOrder } from "@/hooks/useBulkAddPartsToWorkOrder";

type BulkAddPartsDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    workOrderId: string | null;
    workOrderErpId: string | null;
    processId: string | null;
};

type ProcessStepRow = {
    id?: string;
    order?: number;
    step?: { id?: string; name?: string };
};

export function BulkAddPartsDialog({
    open, onOpenChange, workOrderId, workOrderErpId, processId,
}: BulkAddPartsDialogProps) {
    const [quantity, setQuantity] = useState(1);
    const [erpIdStart, setErpIdStart] = useState(1);
    const [stepId, setStepId] = useState<string>("");

    const processQuery = useRetrieveProcessWithSteps(
        { params: { id: processId ?? "" } } as never,
        { enabled: open && !!processId },
    );

    const partTypeId = (processQuery.data as { part_type?: string } | undefined)?.part_type;
    const partTypeQuery = useRetrievePartType(
        { params: { id: partTypeId ?? "" } } as never,
        { enabled: open && !!partTypeId },
    );
    const partType = partTypeQuery.data as
        | { id?: string; name?: string; ID_prefix?: string }
        | undefined;

    const steps = useMemo(() => {
        const raw = (processQuery.data as { process_steps?: ProcessStepRow[] } | undefined)?.process_steps;
        const rows: ProcessStepRow[] = Array.isArray(raw) ? raw : [];
        return [...rows].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    }, [processQuery.data]);

    useEffect(() => {
        if (open && steps.length > 0 && !stepId) {
            const firstId = steps[0]?.step?.id;
            if (firstId) setStepId(firstId);
        }
    }, [open, steps, stepId]);

    useEffect(() => {
        if (!open) {
            setQuantity(1);
            setErpIdStart(1);
            setStepId("");
        }
    }, [open]);

    const preview = useMemo(() => {
        if (!workOrderErpId || quantity < 1) return null;
        const prefix = `${workOrderErpId}-${partType?.ID_prefix || "P"}`;
        const id = (n: number) => `${prefix}${String(n).padStart(4, "0")}`;
        const first = id(erpIdStart);
        if (quantity === 1) return { first, last: null as string | null };
        return { first, last: id(erpIdStart + quantity - 1) };
    }, [workOrderErpId, partType?.ID_prefix, quantity, erpIdStart]);

    const mutation = useBulkAddPartsToWorkOrder();

    function submit() {
        if (!workOrderId || !partType?.id || !stepId) return;
        if (quantity < 1) {
            toast.error("Quantity must be at least 1");
            return;
        }
        mutation.mutate(
            {
                workOrderId,
                part_type: partType.id,
                step: stepId,
                quantity,
                erp_id_start: erpIdStart,
            },
            {
                onSuccess: (data) => {
                    const count = (data as { count?: number })?.count ?? quantity;
                    toast.success(`Created ${count} part${count === 1 ? "" : "s"}`);
                    onOpenChange(false);
                },
                onError: (err) => {
                    toast.error(`Failed: ${(err as Error).message}`);
                },
            },
        );
    }

    const loading = (processQuery.isLoading && !!processId) || partTypeQuery.isLoading;
    const canSubmit =
        !!workOrderId &&
        !!partType?.id &&
        !!stepId &&
        quantity >= 1 &&
        erpIdStart >= 1 &&
        !mutation.isPending;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add parts to {workOrderErpId ?? "work order"}</DialogTitle>
                    <DialogDescription>
                        New parts will be attached to this work order at the chosen step.
                    </DialogDescription>
                </DialogHeader>

                {!processId && (
                    <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                        This work order has no process — assign a process first.
                    </div>
                )}
                {loading && (
                    <div className="text-sm text-muted-foreground">Loading process details…</div>
                )}
                {processQuery.error && (
                    <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
                        Failed to load process: {(processQuery.error as Error).message}
                    </div>
                )}

                {processId && !loading && processQuery.data && (
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                                <Label>Part Type</Label>
                                <div className="mt-1 rounded-md border bg-muted px-2 py-1.5 font-medium">
                                    {partType?.name ?? "—"}
                                </div>
                            </div>
                            <div>
                                <Label htmlFor="ba-step">Start Step</Label>
                                <Select value={stepId} onValueChange={setStepId}>
                                    <SelectTrigger id="ba-step">
                                        <SelectValue placeholder="Select step" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {steps.map((ps) => (
                                            <SelectItem key={ps.step?.id ?? ps.id} value={ps.step?.id ?? ""}>
                                                {ps.step?.name ?? "—"}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label htmlFor="ba-qty">Quantity</Label>
                                <Input
                                    id="ba-qty"
                                    type="number"
                                    min={1}
                                    value={quantity}
                                    onChange={(e) => setQuantity(Number(e.target.value) || 0)}
                                />
                            </div>
                            <div>
                                <Label htmlFor="ba-start">ERP ID Start</Label>
                                <Input
                                    id="ba-start"
                                    type="number"
                                    min={1}
                                    value={erpIdStart}
                                    onChange={(e) => setErpIdStart(Number(e.target.value) || 0)}
                                />
                            </div>
                        </div>

                        {preview && (
                            <div className="rounded-md border bg-muted/30 p-2 text-xs">
                                <div className="font-medium text-muted-foreground">Preview</div>
                                <div className="font-mono">
                                    {preview.last ? `${preview.first} … ${preview.last}` : preview.first}
                                    {" "}({quantity} total)
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={submit} disabled={!canSubmit}>
                        {mutation.isPending ? "Creating…" : `Create ${quantity} part${quantity === 1 ? "" : "s"}`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}