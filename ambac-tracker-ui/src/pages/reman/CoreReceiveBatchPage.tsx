import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, ClipboardPaste, Package, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveCustomers } from "@/hooks/useRetrieveCustomers";
import { useBulkCreateCores, type BulkCoreRow } from "@/hooks/useBulkCreateCores";

type Row = {
    core_number: string;
    core_type: string;
    serial_number: string;
    customer: string;
    source_type: string;
    source_reference: string;
    condition_grade: string;
    condition_notes: string;
    core_credit_value: string;
    received_date: string;
};

type RowErrors = Partial<Record<keyof Row, string>>;

const SOURCE_OPTIONS = [
    { value: "CUSTOMER_RETURN", label: "Customer Return" },
    { value: "PURCHASED", label: "Purchased" },
    { value: "WARRANTY", label: "Warranty" },
    { value: "TRADE_IN", label: "Trade-In" },
];

const GRADE_OPTIONS = [
    { value: "A", label: "Grade A" },
    { value: "B", label: "Grade B" },
    { value: "C", label: "Grade C" },
    { value: "SCRAP", label: "Scrap" },
];

const CUSTOMER_NONE = "__none__";

function emptyRow(): Row {
    return {
        core_number: "",
        core_type: "",
        serial_number: "",
        customer: CUSTOMER_NONE,
        source_type: "CUSTOMER_RETURN",
        source_reference: "",
        condition_grade: "B",
        condition_notes: "",
        core_credit_value: "",
        received_date: new Date().toISOString().slice(0, 10),
    };
}

function validateRow(row: Row): RowErrors {
    const errs: RowErrors = {};
    if (!row.core_number.trim()) errs.core_number = "Required";
    if (!row.core_type) errs.core_type = "Required";
    if (!row.received_date) errs.received_date = "Required";
    if (!row.condition_grade) errs.condition_grade = "Required";
    if (row.core_credit_value && Number.isNaN(parseFloat(row.core_credit_value))) {
        errs.core_credit_value = "Invalid number";
    }
    return errs;
}

function toApiRow(row: Row): BulkCoreRow {
    const out: BulkCoreRow = {
        core_number: row.core_number.trim(),
        core_type: row.core_type,
        received_date: row.received_date,
        source_type: row.source_type,
        condition_grade: row.condition_grade,
    };
    if (row.serial_number.trim()) out.serial_number = row.serial_number.trim();
    if (row.source_reference.trim()) out.source_reference = row.source_reference.trim();
    if (row.condition_notes.trim()) out.condition_notes = row.condition_notes.trim();
    if (row.customer && row.customer !== CUSTOMER_NONE) out.customer = row.customer;
    if (row.core_credit_value.trim()) out.core_credit_value = row.core_credit_value.trim();
    return out;
}

// Column key order matching the help text. Treated as the fallback mapping
// when no header row is detected.
const COLUMN_KEYS: (keyof Row)[] = [
    "core_number", "core_type", "serial_number", "customer",
    "source_type", "source_reference", "condition_grade",
    "condition_notes", "core_credit_value", "received_date",
];

// Accepted header aliases per column. Case- and punctuation-insensitive —
// normalized via normalizeHeader() before lookup.
const HEADER_ALIASES: Record<keyof Row, string[]> = {
    core_number: ["core_number", "corenumber", "core", "core_id", "coreid"],
    core_type: ["core_type", "coretype", "type", "parttype", "part_type"],
    serial_number: ["serial_number", "serialnumber", "serial", "sn"],
    customer: ["customer", "customer_name", "customername"],
    source_type: ["source_type", "sourcetype", "source"],
    source_reference: ["source_reference", "sourceref", "reference", "rma", "po"],
    condition_grade: ["condition_grade", "grade", "condition"],
    condition_notes: ["condition_notes", "notes"],
    core_credit_value: ["core_credit_value", "credit", "creditvalue", "credit_value"],
    received_date: ["received_date", "receiveddate", "received", "date", "receive_date"],
};

function normalizeHeader(s: string): string {
    return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

const ALIAS_TO_KEY: Map<string, keyof Row> = (() => {
    const m = new Map<string, keyof Row>();
    for (const [key, aliases] of Object.entries(HEADER_ALIASES) as [keyof Row, string[]][]) {
        for (const alias of aliases) m.set(normalizeHeader(alias), key);
    }
    return m;
})();

// Split a clipboard paste into rows/cells. Handles spreadsheet-paste TSV and
// falls back to commas for CSV pastes.
export function parsePastedTable(text: string): string[][] {
    const lines = text.replace(/\r\n/g, "\n").split("\n");
    return lines
        .filter((l) => l.length > 0)
        .map((line) => {
            if (line.includes("\t")) return line.split("\t");
            return line.split(",");
        });
}

// If the first cell row looks like a header (every cell maps to a known
// column alias), return the column→key mapping and signal that the first
// data row starts at index 1. Otherwise return null and signal index 0.
export function detectHeaderMapping(firstRow: string[]): {
    columnKeys: (keyof Row | null)[];
    isHeader: boolean;
} {
    const mapped = firstRow.map((cell) => ALIAS_TO_KEY.get(normalizeHeader(cell)) ?? null);
    // Need at least core_number AND core_type recognized to call it a header
    // — keeps a row like "CORE-001,FuelInjector" from being misread.
    const recognized = mapped.filter((k) => k !== null).length;
    const looksLikeHeader =
        recognized === firstRow.length &&
        mapped.includes("core_number") &&
        mapped.includes("core_type");
    return looksLikeHeader
        ? { columnKeys: mapped, isHeader: true }
        : { columnKeys: COLUMN_KEYS.map((k) => k as keyof Row | null), isHeader: false };
}

function rowHasContent(r: Row): boolean {
    return !!(r.core_number.trim() || r.core_type);
}

export function CoreReceiveBatchPage() {
    const navigate = useNavigate();
    const [rows, setRows] = useState<Row[]>([emptyRow()]);
    const [serverErrors, setServerErrors] = useState<Record<number, unknown>>({});

    const { data: partTypesData } = useRetrievePartTypes({ limit: 200 });
    const partTypes = useMemo(
        () => (partTypesData?.results ?? []) as Array<{ id: string; name: string }>,
        [partTypesData],
    );
    const { data: customersData } = useRetrieveCustomers({});
    const customers = useMemo(
        () => (Array.isArray(customersData) ? customersData : []) as Array<{ id: string; name: string }>,
        [customersData],
    );

    const rowErrors = useMemo(() => rows.map(validateRow), [rows]);
    const hasClientErrors = rowErrors.some((e) => Object.keys(e).length > 0);

    // ID sets used to detect cells where a pasted name didn't resolve to a
    // real PartType / Customer — surfaced in the UI as a red trigger with a
    // tooltip explaining the operator needs to re-pick from the dropdown.
    const partTypeIds = useMemo(() => new Set(partTypes.map((p) => p.id)), [partTypes]);
    const customerIds = useMemo(() => new Set(customers.map((c) => c.id)), [customers]);

    function coreTypeUnresolved(row: Row): boolean {
        return !!row.core_type && !partTypeIds.has(row.core_type);
    }
    function customerUnresolved(row: Row): boolean {
        return row.customer !== CUSTOMER_NONE && !!row.customer && !customerIds.has(row.customer);
    }

    const mutation = useBulkCreateCores();

    function updateCell(rowIdx: number, key: keyof Row, value: string) {
        setRows((prev) => prev.map((r, i) => (i === rowIdx ? { ...r, [key]: value } : r)));
        // Clear server-side error for this row when the operator edits it.
        setServerErrors((prev) => {
            if (!(rowIdx in prev)) return prev;
            const next = { ...prev };
            delete next[rowIdx];
            return next;
        });
    }

    function addRow() {
        setRows((prev) => [...prev, emptyRow()]);
    }

    function removeRow(idx: number) {
        setRows((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== idx)));
        setServerErrors((prev) => {
            if (!(idx in prev)) return prev;
            const next: Record<number, unknown> = {};
            for (const [k, v] of Object.entries(prev)) {
                const ki = Number(k);
                if (ki < idx) next[ki] = v;
                else if (ki > idx) next[ki - 1] = v;
            }
            return next;
        });
    }

    function clearAll() {
        setRows([emptyRow()]);
        setServerErrors({});
    }

    function handlePaste(e: React.ClipboardEvent<HTMLElement>) {
        const text = e.clipboardData.getData("text/plain");
        if (!text.includes("\t") && !text.includes("\n")) return; // ordinary paste

        e.preventDefault();
        const cells = parsePastedTable(text);
        if (cells.length === 0) return;

        // If existing rows have data, ask before clobbering. window.confirm
        // is intentional here: this is a destructive, modal moment and the
        // codebase doesn't have a confirm-dialog primitive yet.
        const existingFilled = rows.some(rowHasContent);
        if (existingFilled) {
            const ok = window.confirm(
                `Replace ${rows.length} existing row${rows.length === 1 ? "" : "s"} ` +
                `with ${cells.length} pasted row${cells.length === 1 ? "" : "s"}?`,
            );
            if (!ok) return;
        }

        const firstRow = cells[0] ?? [];
        const { columnKeys, isHeader } = detectHeaderMapping(firstRow);
        const dataRows = isHeader ? cells.slice(1) : cells;

        // PartType / customer pastes come in as names; map to IDs when we can.
        // Defensively skip entries without a string name — the /api/Customers/
        // payload omits `name` for some rows in current demo data.
        const partTypeByName = new Map(
            partTypes
                .filter((p) => typeof p.name === "string" && p.name.length > 0)
                .map((p) => [p.name.toLowerCase(), p.id]),
        );
        const customerByName = new Map(
            customers
                .filter((c) => typeof c.name === "string" && c.name.length > 0)
                .map((c) => [c.name.toLowerCase(), c.id]),
        );

        let unresolved = 0;
        const newRows: Row[] = dataRows.map((cellRow) => {
            const base = emptyRow();
            cellRow.forEach((val, colIdx) => {
                const key = columnKeys[colIdx];
                if (!key) return;
                const v = val.trim();
                if (!v) return;
                if (key === "core_type") {
                    const id = partTypeByName.get(v.toLowerCase());
                    if (id) base.core_type = id;
                    else { base.core_type = v; unresolved++; }
                } else if (key === "customer") {
                    const id = customerByName.get(v.toLowerCase());
                    if (id) base.customer = id;
                    else if (v) { base.customer = v; unresolved++; }
                } else {
                    base[key] = v as never;
                }
            });
            return base;
        });

        if (newRows.length === 0) {
            toast.error("Paste contained only a header row with no data");
            return;
        }

        setRows(newRows);
        setServerErrors({});
        const headerNote = isHeader ? " (matched header row)" : "";
        const unresolvedNote = unresolved > 0
            ? ` · ${unresolved} cell${unresolved === 1 ? "" : "s"} need attention`
            : "";
        toast.success(
            `Pasted ${newRows.length} row${newRows.length === 1 ? "" : "s"}${headerNote}${unresolvedNote}`,
        );
    }

    function submit() {
        if (hasClientErrors) {
            toast.error("Fix invalid rows before submitting");
            return;
        }
        const payload = rows.map(toApiRow);
        mutation.mutate(
            { cores: payload },
            {
                onSuccess: (data) => {
                    const count = (data as { count?: number })?.count ?? payload.length;
                    toast.success(`Received ${count} core${count === 1 ? "" : "s"}`);
                    const today = new Date().toISOString().slice(0, 10);
                    navigate({
                        to: "/reman/cores",
                        search: { received_date: today } as never,
                    });
                },
                onError: (err) => {
                    // Backend returns { detail, errors: [{ index, errors }] }.
                    const body =
                        (err as { response?: { data?: { errors?: Array<{ index: number; errors: unknown }> } } })
                            .response?.data;
                    const list = body?.errors ?? [];
                    const map: Record<number, unknown> = {};
                    for (const entry of list) {
                        if (typeof entry.index === "number" && entry.index >= 0) {
                            map[entry.index] = entry.errors;
                        }
                    }
                    setServerErrors(map);
                    toast.error(`Bulk receive failed (${list.length || 1} issue${list.length === 1 ? "" : "s"})`);
                },
            },
        );
    }

    return (
        <TooltipProvider>
        <div className="max-w-6xl mx-auto space-y-6 p-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" asChild>
                    <Link to="/reman/cores">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                </Button>
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Package className="h-6 w-6" />
                        Receive Cores
                    </h1>
                    <p className="text-muted-foreground">
                        Paste from a spreadsheet or enter rows manually. All rows are saved together.
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Batch Entry</CardTitle>
                    <CardDescription>
                        Required: Core Number, Core Type, Received Date, Condition Grade.
                        Paste cells from a spreadsheet to fill rows. Columns:
                        core_number, core_type, serial_number, customer, source_type,
                        source_reference, condition_grade, condition_notes,
                        core_credit_value, received_date.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div
                        tabIndex={0}
                        onPaste={handlePaste}
                        className={cn(
                            "rounded-md border-2 border-dashed border-muted-foreground/30 bg-muted/20 px-4 py-3",
                            "flex flex-col items-center justify-center gap-1 text-xs text-muted-foreground",
                            "outline-none focus-visible:border-primary focus-visible:bg-primary/5 focus-visible:text-foreground",
                            "cursor-text transition-colors",
                        )}
                        aria-label="Spreadsheet paste target — click to focus then Ctrl/Cmd+V"
                    >
                        <div className="flex items-center gap-1.5">
                            <ClipboardPaste className="h-3.5 w-3.5" />
                            <span className="font-medium">Click here, then Ctrl/Cmd+V to paste rows from a spreadsheet.</span>
                        </div>
                        <span>
                            First row is treated as a header if every cell matches a column name; otherwise we'll
                            map by position.
                        </span>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={addRow}>
                            <Plus className="mr-1 h-4 w-4" />
                            Add Row
                        </Button>
                        <Button size="sm" variant="outline" onClick={clearAll}>
                            Clear All
                        </Button>
                    </div>

                    <div className="overflow-x-auto rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-10">#</TableHead>
                                    <TableHead>Core Number *</TableHead>
                                    <TableHead>Core Type *</TableHead>
                                    <TableHead>Serial</TableHead>
                                    <TableHead>Customer</TableHead>
                                    <TableHead>Source</TableHead>
                                    <TableHead>Source Ref</TableHead>
                                    <TableHead>Grade *</TableHead>
                                    <TableHead>Credit ($)</TableHead>
                                    <TableHead>Received *</TableHead>
                                    <TableHead className="w-10" />
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {rows.map((row, idx) => {
                                    const errs = rowErrors[idx];
                                    const srvErr = serverErrors[idx];
                                    return (
                                        <TableRow key={idx} className={srvErr ? "bg-destructive/5" : undefined}>
                                            <TableCell className="text-xs text-muted-foreground">{idx + 1}</TableCell>
                                            <TableCell>
                                                <Input
                                                    value={row.core_number}
                                                    onChange={(e) => updateCell(idx, "core_number", e.target.value)}
                                                    className={cn("h-8", errs.core_number && "border-destructive")}
                                                />
                                            </TableCell>
                                            <TableCell>
                                                {(() => {
                                                    const unresolved = coreTypeUnresolved(row);
                                                    const trigger = (
                                                        <SelectTrigger
                                                            className={cn(
                                                                "h-8 w-40",
                                                                (errs.core_type || unresolved) && "border-destructive",
                                                            )}
                                                        >
                                                            {unresolved ? (
                                                                <span className="truncate text-destructive">
                                                                    {row.core_type}
                                                                </span>
                                                            ) : (
                                                                <SelectValue placeholder="Select…" />
                                                            )}
                                                        </SelectTrigger>
                                                    );
                                                    const select = (
                                                        <Select
                                                            value={unresolved ? "" : row.core_type}
                                                            onValueChange={(v) => updateCell(idx, "core_type", v)}
                                                        >
                                                            {unresolved ? (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>{trigger}</TooltipTrigger>
                                                                    <TooltipContent>
                                                                        "{row.core_type}" doesn't match any Part Type — pick one
                                                                    </TooltipContent>
                                                                </Tooltip>
                                                            ) : (
                                                                trigger
                                                            )}
                                                            <SelectContent>
                                                                {partTypes.map((p) => (
                                                                    <SelectItem key={p.id} value={p.id}>
                                                                        {p.name}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    );
                                                    return select;
                                                })()}
                                            </TableCell>
                                            <TableCell>
                                                <Input
                                                    value={row.serial_number}
                                                    onChange={(e) => updateCell(idx, "serial_number", e.target.value)}
                                                    className="h-8"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                {(() => {
                                                    const unresolved = customerUnresolved(row);
                                                    const trigger = (
                                                        <SelectTrigger
                                                            className={cn(
                                                                "h-8 w-36",
                                                                unresolved && "border-destructive",
                                                            )}
                                                        >
                                                            {unresolved ? (
                                                                <span className="truncate text-destructive">
                                                                    {row.customer}
                                                                </span>
                                                            ) : (
                                                                <SelectValue />
                                                            )}
                                                        </SelectTrigger>
                                                    );
                                                    return (
                                                        <Select
                                                            value={unresolved ? CUSTOMER_NONE : row.customer}
                                                            onValueChange={(v) => updateCell(idx, "customer", v)}
                                                        >
                                                            {unresolved ? (
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>{trigger}</TooltipTrigger>
                                                                    <TooltipContent>
                                                                        "{row.customer}" doesn't match any Customer — pick one or set "No customer"
                                                                    </TooltipContent>
                                                                </Tooltip>
                                                            ) : (
                                                                trigger
                                                            )}
                                                            <SelectContent>
                                                                <SelectItem value={CUSTOMER_NONE}>No customer</SelectItem>
                                                                {customers.map((c) => (
                                                                    <SelectItem key={c.id} value={c.id}>
                                                                        {c.name}
                                                                    </SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    );
                                                })()}
                                            </TableCell>
                                            <TableCell>
                                                <Select
                                                    value={row.source_type}
                                                    onValueChange={(v) => updateCell(idx, "source_type", v)}
                                                >
                                                    <SelectTrigger className="h-8 w-36">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {SOURCE_OPTIONS.map((o) => (
                                                            <SelectItem key={o.value} value={o.value}>
                                                                {o.label}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </TableCell>
                                            <TableCell>
                                                <Input
                                                    value={row.source_reference}
                                                    onChange={(e) => updateCell(idx, "source_reference", e.target.value)}
                                                    className="h-8 w-28"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Select
                                                    value={row.condition_grade}
                                                    onValueChange={(v) => updateCell(idx, "condition_grade", v)}
                                                >
                                                    <SelectTrigger className={cn("h-8 w-24", errs.condition_grade && "border-destructive")}>
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {GRADE_OPTIONS.map((o) => (
                                                            <SelectItem key={o.value} value={o.value}>
                                                                {o.label}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </TableCell>
                                            <TableCell>
                                                <Input
                                                    type="number"
                                                    step="0.01"
                                                    value={row.core_credit_value}
                                                    onChange={(e) => updateCell(idx, "core_credit_value", e.target.value)}
                                                    className={cn("h-8 w-24", errs.core_credit_value && "border-destructive")}
                                                    placeholder="0.00"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Input
                                                    type="date"
                                                    value={row.received_date}
                                                    onChange={(e) => updateCell(idx, "received_date", e.target.value)}
                                                    className={cn("h-8 w-36", errs.received_date && "border-destructive")}
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    onClick={() => removeRow(idx)}
                                                    disabled={rows.length === 1}
                                                    aria-label="Remove row"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>

                    {Object.entries(serverErrors).length > 0 && (
                        <div className="rounded-md border border-destructive bg-destructive/5 p-3 text-sm">
                            <div className="font-medium text-destructive mb-2">Server validation errors</div>
                            <ul className="space-y-1 text-xs text-destructive">
                                {Object.entries(serverErrors).map(([idx, errs]) => (
                                    <li key={idx} className="font-mono">
                                        Row {Number(idx) + 1}: {JSON.stringify(errs)}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" asChild>
                            <Link to="/reman/cores">Cancel</Link>
                        </Button>
                        <Button onClick={submit} disabled={mutation.isPending || hasClientErrors}>
                            {mutation.isPending ? "Submitting…" : `Submit ${rows.length} core${rows.length === 1 ? "" : "s"}`}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
        </TooltipProvider>
    );
}

export default CoreReceiveBatchPage;