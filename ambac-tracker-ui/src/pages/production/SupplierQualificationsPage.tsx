import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Plus } from "lucide-react";
import {
    useListSupplierQualifications, useGrantQualification, useSuspendQualification,
    useDisqualifyQualification,
} from "@/hooks/useSupplierQualifications";

const STATUS_TONE: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    APPROVED: "default", CONDITIONAL: "secondary", PENDING: "outline",
    SUSPENDED: "destructive", EXPIRED: "outline", DISQUALIFIED: "destructive",
};

const STATUS_FILTERS = ["", "PENDING", "APPROVED", "CONDITIONAL", "SUSPENDED", "EXPIRED", "DISQUALIFIED"];

function expiryTone(expiry: string | null): string {
    if (!expiry) return "";
    const days = Math.ceil((new Date(expiry).getTime() - Date.now()) / 86_400_000);
    if (days < 0) return "text-destructive font-medium";
    if (days <= 30) return "text-amber-600 font-medium";
    return "";
}

type ActionKind = "grant" | "suspend" | "disqualify";

export function SupplierQualificationsPage() {
    const [status, setStatus] = useState("");
    const [search, setSearch] = useState("");
    const { data, isLoading } = useListSupplierQualifications({
        status: status || undefined,
        search: search || undefined,
        limit: 200,
    });

    const grant = useGrantQualification();
    const suspend = useSuspendQualification();
    const disqualify = useDisqualifyQualification();

    const [dialog, setDialog] = useState<{ kind: ActionKind; id: string; supplier: string } | null>(null);
    const [conditional, setConditional] = useState(false);
    const [expiry, setExpiry] = useState("");
    const [reason, setReason] = useState("");

    const openDialog = (kind: ActionKind, id: string, supplier: string) => {
        setConditional(false); setExpiry(""); setReason("");
        setDialog({ kind, id, supplier });
    };

    const submit = async () => {
        if (!dialog) return;
        try {
            if (dialog.kind === "grant") {
                await grant.mutateAsync({ id: dialog.id, conditional, expiry_date: expiry || null });
                toast.success("Qualification granted");
            } else if (dialog.kind === "suspend") {
                await suspend.mutateAsync({ id: dialog.id, reason });
                toast.success("Qualification suspended");
            } else {
                await disqualify.mutateAsync({ id: dialog.id, reason });
                toast.success("Supplier disqualified");
            }
            setDialog(null);
        } catch {
            toast.error("Action failed");
        }
    };

    const rows = (data as { results?: any[] } | undefined)?.results ?? [];

    return (
        <div className="space-y-4 p-2">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight">Approved Supplier List</h1>
                    <p className="text-sm text-muted-foreground">
                        Supplier qualifications by scope — status, basis, and expiry. Receiving holds lots from
                        unqualified suppliers for part types that require qualification.
                    </p>
                </div>
                <Link to="/production/supplier-qualifications/new">
                    <Button size="sm"><Plus className="mr-1 h-4 w-4" /> New qualification</Button>
                </Link>
            </div>

            <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1.5">
                    <Label className="text-xs">Status</Label>
                    <Select value={status || "ALL"} onValueChange={(v) => setStatus(v === "ALL" ? "" : v)}>
                        <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            {STATUS_FILTERS.map((s) => (
                                <SelectItem key={s || "ALL"} value={s || "ALL"}>{s || "All statuses"}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1.5">
                    <Label className="text-xs">Search</Label>
                    <Input className="w-60" placeholder="Supplier, scope, number…" value={search}
                        onChange={(e) => setSearch(e.target.value)} />
                </div>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Number</TableHead>
                            <TableHead>Supplier</TableHead>
                            <TableHead>Scope</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Basis</TableHead>
                            <TableHead>Expiry</TableHead>
                            <TableHead className="w-10" />
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {isLoading ? (
                            <TableRow><TableCell colSpan={7} className="text-muted-foreground">Loading…</TableCell></TableRow>
                        ) : rows.length === 0 ? (
                            <TableRow><TableCell colSpan={7} className="text-muted-foreground">No qualifications.</TableCell></TableRow>
                        ) : rows.map((q) => (
                            <TableRow key={q.id}>
                                <TableCell className="font-mono text-xs">{q.qualification_number}</TableCell>
                                <TableCell>{q.supplier_name}</TableCell>
                                <TableCell>{q.scope_display}</TableCell>
                                <TableCell><Badge variant={STATUS_TONE[q.status] ?? "outline"}>{q.status_display ?? q.status}</Badge></TableCell>
                                <TableCell className="text-muted-foreground">{q.basis || "—"}</TableCell>
                                <TableCell className={expiryTone(q.expiry_date)}>{q.expiry_date ?? "—"}</TableCell>
                                <TableCell>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem asChild>
                                                <Link to="/production/supplier-qualifications/$qualId/edit" params={{ qualId: String(q.id) }}>Edit</Link>
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => openDialog("grant", String(q.id), q.supplier_name)}>Grant…</DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => openDialog("suspend", String(q.id), q.supplier_name)}>Suspend…</DropdownMenuItem>
                                            <DropdownMenuItem className="text-destructive"
                                                onClick={() => openDialog("disqualify", String(q.id), q.supplier_name)}>Disqualify…</DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            <Dialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {dialog?.kind === "grant" && `Grant qualification — ${dialog.supplier}`}
                            {dialog?.kind === "suspend" && `Suspend — ${dialog.supplier}`}
                            {dialog?.kind === "disqualify" && `Disqualify — ${dialog.supplier}`}
                        </DialogTitle>
                    </DialogHeader>
                    {dialog?.kind === "grant" ? (
                        <div className="space-y-4">
                            <div className="flex items-center gap-2">
                                <Checkbox id="conditional" checked={conditional} onCheckedChange={(c) => setConditional(!!c)} />
                                <Label htmlFor="conditional">Conditional approval (probation)</Label>
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="expiry">Expiry date (optional)</Label>
                                <Input id="expiry" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-1.5">
                            <Label htmlFor="reason">Reason</Label>
                            <Textarea id="reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialog(null)}>Cancel</Button>
                        <Button onClick={submit}
                            variant={dialog?.kind === "disqualify" ? "destructive" : "default"}>
                            {dialog?.kind === "grant" ? "Grant" : dialog?.kind === "suspend" ? "Suspend" : "Disqualify"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
