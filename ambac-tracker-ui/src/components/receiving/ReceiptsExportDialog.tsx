import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCheck, Download } from "lucide-react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { getCookie } from "@/lib/utils";

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

// The local day, YYYY-MM-DD (toISOString is UTC, a day off in the evening).
const isoDay = (d: Date) => d.toLocaleDateString("en-CA");

/**
 * What the dock received, by PO line, for posting the goods receipts in the ERP. The PO
 * is the ERP's and the receipt is ours; the ERP takes no feed, so this is the sheet a
 * person carries back — and, once they've keyed it in, UQMES records that it was posted,
 * so the next sheet holds only what's new. Only a delivery whose decision is final can
 * be posted; one whose numbers moved after posting comes back as "changed since posted".
 */
export function ReceiptsExportDialog({ open, onOpenChange }: Props) {
    const queryClient = useQueryClient();
    const today = new Date();
    const [start, setStart] = useState(isoDay(new Date(today.getTime() - 29 * 86_400_000)));
    const [end, setEnd] = useState(isoDay(today));
    const [poOnly, setPoOnly] = useState(true);
    const [unpostedOnly, setUnpostedOnly] = useState(true);
    const [busy, setBusy] = useState(false);
    const [downloaded, setDownloaded] = useState(false);

    const valid = start !== "" && end !== "" && start <= end;
    const queries = {
        start, end,
        ...(poOnly ? { po_only: true } : {}),
        ...(unpostedOnly ? { unposted_only: true } : {}),
    };
    const rowsQ = useQuery({
        queryKey: ["receipts", queries],
        queryFn: () => api.api_Receipts_list({ queries }),
        enabled: open && valid,
    });
    const rows = rowsQ.data ?? [];
    const count = (s: string) => rows.filter((r) => r.erp_status === s).length;
    const toPost = rows.filter((r) => r.erp_status === "Ready to post" || r.erp_status === "Changed since posted");

    const markPosted = useMutation({
        mutationFn: () => api.api_Receipts_mark_posted_create(
            { lot_ids: toPost.map((r) => r.lot_id) },
            { headers: { "X-CSRFToken": getCookie("csrftoken") } }),
        onSuccess: (r) => {
            toast.success(`${r.marked} deliver${r.marked === 1 ? "y" : "ies"} marked as posted to the ERP.`);
            setDownloaded(false);
            queryClient.invalidateQueries({ queryKey: ["receipts"] });
        },
        onError: () => toast.error("Couldn't mark them posted."),
    });

    const download = async () => {
        setBusy(true);
        try {
            const resp = await api.axios.get("/api/MaterialLots/receipts-export/", {
                params: queries, responseType: "blob",
            });
            downloadBlob(resp.data, `receipts_${start}_${end}.xlsx`);
            setDownloaded(true);
        } catch (e) {
            toast.error(await blobErrorMessage(e, "Couldn't build the receipts sheet."));
        } finally {
            setBusy(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) setDownloaded(false); onOpenChange(o); }}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Receipts for the ERP</DialogTitle>
                    <DialogDescription>
                        One row per delivery, by PO line: what was received, accepted, rejected or is
                        still awaiting a decision. Key it into the ERP, then mark it posted here.
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
                    <label className="col-span-2 flex items-center gap-2 text-sm">
                        <Checkbox checked={unpostedOnly} onCheckedChange={(v) => setUnpostedOnly(v === true)} />
                        Leave out what&rsquo;s already posted
                    </label>
                </div>
                <div className="flex flex-wrap gap-2 text-sm">
                    {rowsQ.isLoading ? <span className="text-muted-foreground">Counting…</span> : (
                        <>
                            <Badge>{count("Ready to post")} ready to post</Badge>
                            {count("Changed since posted") > 0 && (
                                <Badge variant="destructive">{count("Changed since posted")} changed since posted</Badge>
                            )}
                            {count("Awaiting decision") > 0 && (
                                <Badge variant="outline">{count("Awaiting decision")} awaiting a decision</Badge>
                            )}
                            {!unpostedOnly && count("Posted") > 0 && (
                                <Badge variant="secondary">{count("Posted")} posted</Badge>
                            )}
                        </>
                    )}
                </div>
                {downloaded && toPost.length > 0 && (
                    <p className="rounded-md border bg-muted/40 p-3 text-sm">
                        Once these {toPost.length} are keyed into the ERP, mark them posted — the next
                        sheet then holds only what&rsquo;s new. Ones awaiting a decision stay out until
                        they&rsquo;re decided.
                    </p>
                )}
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Close</Button>
                    {downloaded && toPost.length > 0 && (
                        <Button variant="secondary" onClick={() => markPosted.mutate()} disabled={markPosted.isPending}>
                            <CheckCheck className="mr-1.5 h-4 w-4" />
                            {markPosted.isPending ? "Marking…" : `Mark ${toPost.length} as posted`}
                        </Button>
                    )}
                    <Button onClick={download} disabled={!valid || busy || rows.length === 0}>
                        <Download className="mr-1.5 h-4 w-4" />
                        {busy ? "Building…" : "Download"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
