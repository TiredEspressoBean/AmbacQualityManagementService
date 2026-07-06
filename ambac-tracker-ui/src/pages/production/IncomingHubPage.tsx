/**
 * Incoming Inspection — one unified worklist (SAP QM QA32-style).
 *
 * A single queue across inbound-inspection sources, keyed by a Source column:
 *   - Purchased lot   — MaterialLot awaiting receiving inspection (Flow A)
 *   - Outside process — OutsideProcessShipment out / returned (Flow B)
 *
 * Both back the same subject-agnostic DWI inspection runtime; this replaces the
 * old two-tab hub with one list + Source/Status filters (design doc §4). Inspect
 * dispatches to the right runtime by source; the routing difference stays
 * invisible to the inspector.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Loader2, PackageSearch } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api/generated";
import { useIncomingInspection, type IncomingInspectionRow } from "@/hooks/useIncomingInspection";

const SOURCE_LABEL: Record<string, string> = {
    PURCHASED_LOT: "Purchased lot",
    OUTSIDE_PROCESS: "Outside process",
};

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    "Awaiting inspection": "secondary",
    "At vendor": "outline",
    Held: "destructive",
};

export function IncomingHubPage() {
    const navigate = useNavigate();
    const { data, isLoading } = useIncomingInspection();
    const [source, setSource] = useState<string>("ALL");
    const [status, setStatus] = useState<string>("ALL");
    const [q, setQ] = useState("");
    const [openingId, setOpeningId] = useState<string | null>(null);

    const rows = data ?? [];
    const statuses = useMemo(
        () => Array.from(new Set(rows.map((r) => r.status_display))).sort(),
        [rows],
    );

    const filtered = rows.filter((r) => {
        if (source !== "ALL" && r.source !== source) return false;
        if (status !== "ALL" && r.status_display !== status) return false;
        if (q) {
            const hay = `${r.reference} ${r.item} ${r.supplier}`.toLowerCase();
            if (!hay.includes(q.toLowerCase())) return false;
        }
        return true;
    });

    const inspect = async (row: IncomingInspectionRow) => {
        if (row.source === "PURCHASED_LOT") {
            navigate({ to: "/production/receiving-inspection/$lotId", params: { lotId: row.id } });
            return;
        }
        // Outside process: resolve the return inspection's execution, then open the runtime.
        setOpeningId(row.id);
        try {
            const plan = await api.api_OutsideProcessShipments_sample_plan_retrieve({
                params: { id: row.id },
            } as never) as { step_id?: string; step_execution_id?: string };
            if (plan.step_id && plan.step_execution_id) {
                navigate({
                    to: "/operator/steps/$stepId/substeps",
                    params: { stepId: String(plan.step_id) },
                    search: { execution: String(plan.step_execution_id), osp_shipment: row.id, at: 0 } as never,
                });
            } else {
                toast.error("No open return inspection for this shipment.");
            }
        } catch {
            toast.error("Couldn't open the return inspection.");
        } finally {
            setOpeningId(null);
        }
    };

    return (
        <div className="space-y-4 p-6">
            <div className="flex items-center gap-3">
                <PackageSearch className="h-5 w-5 text-sky-600" />
                <h1 className="text-2xl font-semibold">Incoming Inspection</h1>
            </div>
            <p className="text-sm text-muted-foreground">
                Everything awaiting inbound inspection — purchased material and parts back
                from a subcontract vendor — in one queue. Inspect opens the same runtime for both.
            </p>

            <div className="flex flex-wrap items-center gap-2">
                <Input placeholder="Search ref, item, supplier…" value={q}
                    onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
                <Select value={source} onValueChange={setSource}>
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="ALL">All sources</SelectItem>
                        <SelectItem value="PURCHASED_LOT">Purchased lot</SelectItem>
                        <SelectItem value="OUTSIDE_PROCESS">Outside process</SelectItem>
                    </SelectContent>
                </Select>
                <Select value={status} onValueChange={setStatus}>
                    <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="ALL">All statuses</SelectItem>
                        {statuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                </Select>
            </div>

            <div className="rounded-lg border bg-card">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Source</TableHead>
                            <TableHead>Ref</TableHead>
                            <TableHead>Item</TableHead>
                            <TableHead>Supplier</TableHead>
                            <TableHead>Qty</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Received</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow><TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                                <Loader2 className="mx-auto h-4 w-4 animate-spin" />
                            </TableCell></TableRow>
                        ) : filtered.length === 0 ? (
                            <TableRow><TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                                Nothing awaiting incoming inspection.
                            </TableCell></TableRow>
                        ) : filtered.map((r) => (
                            <TableRow key={`${r.source}:${r.id}`}>
                                <TableCell>
                                    <Badge variant="outline" className={
                                        r.source === "OUTSIDE_PROCESS" ? "border-sky-400 text-sky-700" : ""
                                    }>{SOURCE_LABEL[r.source] ?? r.source}</Badge>
                                </TableCell>
                                <TableCell className="font-mono text-xs font-medium">{r.reference}</TableCell>
                                <TableCell>{r.item || "—"}</TableCell>
                                <TableCell>{r.supplier || "—"}</TableCell>
                                <TableCell className="tabular-nums">{r.quantity ?? "—"}</TableCell>
                                <TableCell>
                                    <Badge variant={STATUS_VARIANT[r.status_display] ?? "outline"}>
                                        {r.status_display}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-muted-foreground">
                                    {r.received_at ? r.received_at.slice(0, 10) : "—"}
                                </TableCell>
                                <TableCell className="text-right">
                                    {r.status_display === "At vendor" ? (
                                        <span className="text-[10px] text-muted-foreground">at vendor</span>
                                    ) : (
                                        <Button size="sm" disabled={openingId === r.id} onClick={() => inspect(r)}>
                                            {openingId === r.id && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                                            Inspect
                                        </Button>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
