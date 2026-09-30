import { useState } from "react";
import { toast } from "sonner";
import { Download, Upload } from "lucide-react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/generated";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { useImportExpectedReceipts } from "@/hooks/useReceivingMutations";
import type { Schema } from "@/lib/api/types";

type Result = Schema<"ExpectedReceiptImportResult">;

const OUTCOME_LABEL: Record<string, string> = {
    CREATED: "Added",
    UPDATED: "Updated",
    UNCHANGED: "No change",
    ALREADY_RECEIVED: "Already received",
    ERROR: "Error",
};

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

/**
 * Upload open purchase-order lines typed up from the ERP. The ERP can't send them, so a
 * person copies them into the template. Matched on PO number + line: re-uploading
 * updates rather than duplicates, a line missing from the sheet is left alone, and a
 * line already received is never put back on order. Bad rows are listed; the rest land.
 */
export function ImportExpectedReceiptsDialog({ open, onOpenChange }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<Result | null>(null);
    const upload = useImportExpectedReceipts();

    const downloadTemplate = async () => {
        try {
            const resp = await api.axios.get("/api/MaterialLots/import-expected-template/",
                { responseType: "blob" });
            downloadBlob(resp.data, "expected_receipts_template.csv");
        } catch (e) {
            toast.error(await blobErrorMessage(e, "Couldn't download the template."));
        }
    };

    const submit = () => {
        if (!file) return;
        upload.mutate(file, {
            onSuccess: (r) => {
                setResult(r);
                if (r.errors === 0) toast.success(`${r.created} added, ${r.updated} updated.`);
            },
            onError: (err: unknown) => {
                const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                toast.error(detail ?? "Couldn't read that file.");
            },
        });
    };

    const close = (o: boolean) => {
        if (!o) { setFile(null); setResult(null); }
        onOpenChange(o);
    };

    const problems = (result?.rows ?? []).filter((r) => r.outcome === "ERROR" || r.outcome === "ALREADY_RECEIVED");

    return (
        <Dialog open={open} onOpenChange={close}>
            <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Import open PO lines</DialogTitle>
                    <DialogDescription>
                        Each row becomes an expected receipt, matched on PO number and line.
                        Uploading again updates quantities and dates. Nothing is closed by
                        being left off the sheet — close short at receiving instead.
                    </DialogDescription>
                </DialogHeader>

                {!result ? (
                    <div className="space-y-3">
                        <Button variant="outline" size="sm" onClick={downloadTemplate}>
                            <Download className="mr-1.5 h-4 w-4" /> Template (.csv)
                        </Button>
                        <p className="text-xs text-muted-foreground">
                            Columns: PO Number, PO Line, Item (part number or name), Quantity (still to
                            come), Promised Date, and optionally Supplier and Unit.
                        </p>
                        <Input type="file" accept=".csv,.xlsx"
                            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                    </div>
                ) : (
                    <div className="space-y-3 text-sm">
                        <div className="flex flex-wrap gap-2">
                            <Badge>{result.created} added</Badge>
                            <Badge variant="secondary">{result.updated} updated</Badge>
                            <Badge variant="outline">{result.unchanged} no change</Badge>
                            {result.already_received > 0 && <Badge variant="outline">{result.already_received} already received</Badge>}
                            {result.errors > 0 && <Badge variant="destructive">{result.errors} not imported</Badge>}
                        </div>
                        {problems.length > 0 && (
                            <div className="overflow-x-auto rounded-md border">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b bg-muted/40 text-left text-muted-foreground">
                                            <th className="p-2 font-medium">Row</th>
                                            <th className="p-2 font-medium">PO / line</th>
                                            <th className="p-2 font-medium">Result</th>
                                            <th className="p-2 font-medium">Why</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {problems.map((r) => (
                                            <tr key={r.row} className="border-b last:border-0">
                                                <td className="p-2 tabular-nums">{r.row}</td>
                                                <td className="p-2 font-mono">{r.erp_po_number || "—"} / {r.erp_po_line || "—"}</td>
                                                <td className="p-2">{OUTCOME_LABEL[r.outcome] ?? r.outcome}</td>
                                                <td className="p-2 text-muted-foreground">{r.detail}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter>
                    {!result ? (
                        <>
                            <Button variant="outline" onClick={() => close(false)} disabled={upload.isPending}>Cancel</Button>
                            <Button onClick={submit} disabled={!file || upload.isPending}>
                                <Upload className="mr-1.5 h-4 w-4" />
                                {upload.isPending ? "Importing…" : "Import"}
                            </Button>
                        </>
                    ) : (
                        <Button onClick={() => close(false)}>Done</Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
