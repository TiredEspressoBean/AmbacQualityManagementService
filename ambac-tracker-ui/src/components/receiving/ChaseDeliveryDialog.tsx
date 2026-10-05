import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Mail } from "lucide-react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

export type ChaseTarget = {
    lot_id: string;
    item_name: string;
    supplier_name?: string | null;
    supplier_contact?: string | null;
    supplier_contact_email?: string | null;
    erp_po_number?: string | null;
    erp_po_line?: string | null;
    promised_date?: string | null;
    chase_note?: string | null;
};

/** A mailto: for chasing one delivery — opens the buyer's own mail client. */
export function chaseMailto(t: ChaseTarget): string | null {
    if (!t.supplier_contact_email) return null;
    const po = t.erp_po_number ? `PO ${t.erp_po_number}${t.erp_po_line ? ` line ${t.erp_po_line}` : ""}` : "our order";
    const subject = `Delivery status — ${po} (${t.item_name})`;
    const body = `Hello${t.supplier_contact ? ` ${t.supplier_contact}` : ""},\n\n` +
        `Could you confirm when ${po} for ${t.item_name}` +
        `${t.promised_date ? `, promised for ${t.promised_date},` : ""} will ship?\n\nThank you.`;
    return `mailto:${t.supplier_contact_email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

/**
 * The buyer chased a delivery: what the supplier said, and a new promised date if they
 * gave one. The first promise is kept — on-time delivery is judged against it, so a
 * supplier who slips twice doesn't score as on time.
 */
export function ChaseDeliveryDialog({ target, open, onOpenChange }: {
    target: ChaseTarget; open: boolean; onOpenChange: (o: boolean) => void;
}) {
    const qc = useQueryClient();
    const [note, setNote] = useState("");
    const [promised, setPromised] = useState("");
    const chase = useMutation({
        // Multipart (see useLocations): send the date only when one was given.
        mutationFn: () => api.api_MaterialLots_chase_create(
            { note, ...(promised ? { promised_date: promised } : {}) }, { params: { id: target.lot_id } }),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["late-deliveries"] });
            void qc.invalidateQueries({ queryKey: ["material-lots"] });
            void qc.invalidateQueries({ queryKey: ["material-lot"] });
        },
    });
    const mailto = chaseMailto(target);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Chase · {target.item_name}</DialogTitle>
                    <DialogDescription>
                        {target.supplier_name ?? "No supplier"}
                        {target.erp_po_number ? ` · PO ${target.erp_po_number}${target.erp_po_line ? `/${target.erp_po_line}` : ""}` : ""}
                        {target.promised_date ? ` · promised ${target.promised_date}` : ""}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-1">
                    {mailto && (
                        <Button variant="outline" size="sm" asChild>
                            <a href={mailto}><Mail className="mr-1 h-4 w-4" /> Email {target.supplier_contact ?? target.supplier_contact_email}</a>
                        </Button>
                    )}
                    {target.chase_note && (
                        <p className="text-xs text-muted-foreground">Last time: {target.chase_note}</p>
                    )}
                    <div className="space-y-1.5">
                        <Label htmlFor="ch-note">What they said</Label>
                        <Textarea id="ch-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                            placeholder="e.g. Ships Thursday, tracking to follow" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="ch-date">New promised date <span className="text-muted-foreground">(if they gave one)</span></Label>
                        <Input id="ch-date" type="date" value={promised} onChange={(e) => setPromised(e.target.value)} />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={chase.isPending}>Cancel</Button>
                    <Button disabled={chase.isPending || !note.trim()}
                        onClick={() => chase.mutate(undefined, {
                            onSuccess: () => { toast.success("Chase recorded."); setNote(""); setPromised(""); onOpenChange(false); },
                            onError: (e) => toast.error(errorOf(e, "Could not record the chase")),
                        })}>
                        {chase.isPending ? "Saving…" : "Record chase"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
