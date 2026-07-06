/**
 * Send-out dialog for outside processing (Flow B) — shared by the WO control-page
 * panel and the shipper board. Quantity-first (the operator/shipper says "how many",
 * not "which ones"); a collapsible per-serial picker covers shops that track units.
 * Writes one OutsideProcessShipment.
 */
import { useState } from "react";
import { Loader2, Minus, Plus, ChevronRight } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useSendPartsOut } from "@/hooks/useOutsideProcess";

export type SendablePart = { id: string; label: string; status?: string };

export function SendPartsOutDialog({
    stepId, stepName, defaultSupplierId, parts, onClose, onSent,
}: {
    stepId: string;
    stepName: string;
    defaultSupplierId?: string | null;
    parts: SendablePart[];
    onClose: () => void;
    onSent?: () => void;
}) {
    const sendOut = useSendPartsOut();
    const { data: companiesData } = useRetrieveCompanies({ limit: 200 } as never);

    const total = parts.length;
    const [quantity, setQuantity] = useState(total);
    const [pickSpecific, setPickSpecific] = useState(false);
    const [selected, setSelected] = useState<Set<string>>(() => new Set(parts.map((p) => p.id)));
    const [supplierId, setSupplierId] = useState<string>(defaultSupplierId ?? "");
    const [reference, setReference] = useState("");

    const companies = (companiesData?.results ?? []) as { id: string; name: string }[];

    const partIds = pickSpecific ? Array.from(selected) : parts.slice(0, quantity).map((p) => p.id);
    const count = partIds.length;

    const clampQty = (n: number) => Math.max(1, Math.min(total, n));
    const togglePickSpecific = () =>
        setPickSpecific((open) => {
            if (!open) setSelected(new Set(parts.slice(0, quantity).map((p) => p.id)));
            return !open;
        });
    const toggle = (id: string) =>
        setSelected((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });

    const handleSend = () => {
        if (count === 0) { toast.error("Choose at least one part to send out."); return; }
        if (!supplierId) { toast.error("Pick a subcontract vendor."); return; }
        sendOut.mutate(
            { step: stepId, part_ids: partIds, supplier: supplierId, reference: reference || undefined },
            {
                onSuccess: (shipment) => {
                    toast.success(
                        `${shipment.shipment_number} — ${count} part${count === 1 ? "" : "s"} sent to ${shipment.supplier_name}`,
                    );
                    onSent?.();
                    onClose();
                },
            },
        );
    };

    return (
        <Dialog open onOpenChange={(o) => !o && onClose()}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Send out — {stepName}</DialogTitle>
                    <DialogDescription>
                        Ship parts to a subcontract vendor. They move to “At outside
                        process” until you receive them back for inspection.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="space-y-1.5">
                        <Label>Vendor</Label>
                        <Select value={supplierId} onValueChange={setSupplierId}>
                            <SelectTrigger><SelectValue placeholder="Select a vendor" /></SelectTrigger>
                            <SelectContent>
                                {companies.map((c) => (
                                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="osp-ref">PO / packing-slip reference</Label>
                        <Input id="osp-ref" value={reference}
                            onChange={(e) => setReference(e.target.value)} placeholder="e.g. PO-1042" />
                    </div>

                    {!pickSpecific && (
                        <div className="flex items-center justify-between">
                            <Label>How many?</Label>
                            <div className="flex items-center gap-2">
                                <Button type="button" size="icon" variant="outline" className="h-8 w-8"
                                    disabled={quantity <= 1} onClick={() => setQuantity((q) => clampQty(q - 1))}>
                                    <Minus className="h-3.5 w-3.5" />
                                </Button>
                                <span className="w-10 text-center text-sm font-medium tabular-nums">{quantity}</span>
                                <Button type="button" size="icon" variant="outline" className="h-8 w-8"
                                    disabled={quantity >= total} onClick={() => setQuantity((q) => clampQty(q + 1))}>
                                    <Plus className="h-3.5 w-3.5" />
                                </Button>
                                <span className="ml-1 text-xs text-muted-foreground">of {total} ready</span>
                            </div>
                        </div>
                    )}

                    <div>
                        <button type="button"
                            className="flex items-center gap-1 text-xs text-primary hover:underline"
                            onClick={togglePickSpecific}>
                            <ChevronRight className={cn("h-3 w-3 transition-transform", pickSpecific && "rotate-90")} />
                            {pickSpecific ? `Pick specific units (${selected.size}/${total})` : "Pick specific units (optional)"}
                        </button>
                        {pickSpecific && (
                            <ScrollArea className="mt-2 h-40 rounded border">
                                <div className="divide-y">
                                    {parts.map((p) => (
                                        <label key={p.id}
                                            className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent/40">
                                            <Checkbox checked={selected.has(p.id)} onCheckedChange={() => toggle(p.id)} />
                                            <span className="font-mono text-xs">{p.label}</span>
                                            {p.status && (
                                                <span className="ml-auto text-[10px] text-muted-foreground">{p.status}</span>
                                            )}
                                        </label>
                                    ))}
                                </div>
                            </ScrollArea>
                        )}
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={onClose}>Cancel</Button>
                    <Button onClick={handleSend} disabled={sendOut.isPending || count === 0}>
                        {sendOut.isPending && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                        Send {count} out
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
