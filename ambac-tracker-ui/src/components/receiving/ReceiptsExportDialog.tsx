import { useState } from "react";
import { toast } from "sonner";
import { Download } from "lucide-react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

// The local day, YYYY-MM-DD (toISOString is UTC, a day off in the evening).
const isoDay = (d: Date) => d.toLocaleDateString("en-CA");

/**
 * What the dock received, by PO line, for posting the goods receipts in the ERP. The PO
 * is the ERP's and the receipt is ours; the ERP takes no feed, so this is the sheet a
 * person carries back: received, accepted, rejected and still-awaiting per delivery.
 */
export function ReceiptsExportDialog({ open, onOpenChange }: Props) {
    const today = new Date();
    const [start, setStart] = useState(isoDay(new Date(today.getTime() - 6 * 86_400_000)));
    const [end, setEnd] = useState(isoDay(today));
    const [poOnly, setPoOnly] = useState(true);
    const [busy, setBusy] = useState(false);

    const download = async () => {
        setBusy(true);
        try {
            const resp = await api.axios.get("/api/MaterialLots/receipts-export/", {
                params: { start, end, ...(poOnly ? { po_only: "true" } : {}) },
                responseType: "blob",
            });
            downloadBlob(resp.data, `receipts_${start}_${end}.xlsx`);
            onOpenChange(false);
        } catch (e) {
            toast.error(await blobErrorMessage(e, "Couldn't build the receipts sheet."));
        } finally {
            setBusy(false);
        }
    };

    const valid = start !== "" && end !== "" && start <= end;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Receipts for the ERP</DialogTitle>
                    <DialogDescription>
                        One row per delivery, by PO line: what was received, accepted, rejected or is
                        still awaiting a decision — to post the goods receipts in the ERP.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid grid-cols-2 gap-3 py-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="rx-start">Received from</Label>
                        <Input id="rx-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rx-end">to</Label>
                        <Input id="rx-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
                    </div>
                    <label className="col-span-2 flex items-center gap-2 text-sm">
                        <Checkbox checked={poOnly} onCheckedChange={(v) => setPoOnly(v === true)} />
                        Only deliveries received against a PO
                    </label>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
                    <Button onClick={download} disabled={!valid || busy}>
                        <Download className="mr-1.5 h-4 w-4" />
                        {busy ? "Building…" : "Download"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
