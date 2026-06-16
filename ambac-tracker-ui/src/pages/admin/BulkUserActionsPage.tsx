/**
 * Bulk user actions — full-page workbook surface.
 *
 * Single endpoint behind it (to be built) accepts a unified set of row actions:
 *   invite, group reassignment, activate, deactivate, etc.
 * The "action" is implied by which fields the row populates plus an
 * optional `action` column for explicit verbs (e.g. action=deactivate).
 *
 * Two input modes share the same submit:
 * - **Manual entry**: in-page editable table.
 * - **Upload workbook**: CSV/XLSX file picker; sample template available.
 *
 * Backend is not yet wired — Submit + Upload only emit a toast describing
 * what *would* happen. This page exists to define the spec.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import {
    Plus,
    Trash2,
    Upload,
    Download,
    AlertCircle,
    ArrowLeft,
    UserPlus,
    Copy,
    Check,
    Link as LinkIcon,
} from "lucide-react";
import { toast } from "sonner";

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import {
    useBulkReconcileUsers,
    fetchBulkReconcileStatus,
    type BulkReconcileResultRow,
} from "@/hooks/useBulkReconcileUsers";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

// ---------------------------------------------------------------------------
// Row model — describes desired state of a user. Behavior is inferred:
//   • email not in tenant → create user + send invite
//   • email in tenant     → update fields/groups/status to match this row
//   • empty cell          → no change to that field
// Re-running the same workbook is a no-op once state already matches.
// ---------------------------------------------------------------------------

type RowStatus = "Active" | "Inactive";

type WorkbookRow = {
    id: string; // local-only stable id for React keys
    email: string;
    first_name: string;
    last_name: string;
    group: string; // group name (semicolon-separated in CSV upload mode)
    status: RowStatus;
    message: string; // included in invite email when creating a new user
};

function makeRow(partial: Partial<WorkbookRow> = {}): WorkbookRow {
    return {
        id:
            typeof crypto !== "undefined" && "randomUUID" in crypto
                ? crypto.randomUUID()
                : Math.random().toString(36).slice(2),
        email: "",
        first_name: "",
        last_name: "",
        group: "",
        status: "Active",
        message: "",
        ...partial,
    };
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function rowProblems(row: WorkbookRow): string[] {
    const problems: string[] = [];
    if (!row.email.trim()) problems.push("email required");
    else if (!EMAIL_RE.test(row.email.trim())) problems.push("email format");
    return problems;
}

const STATUS_VALUES: RowStatus[] = ["Active", "Inactive"];

/** Inline copy button for a single invite link. Own hook instance so the
 *  checkmark only flips on the row that was clicked. */
function CopyLinkButton({ url }: { url: string }) {
    const { isCopied, copyToClipboard } = useCopyToClipboard();
    return (
        <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-1.5 text-[11px] shrink-0"
            onClick={() => copyToClipboard(url)}
        >
            {isCopied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
            Copy
        </Button>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function BulkUserActionsPage() {
    const navigate = useNavigate();
    const [rows, setRows] = useState<WorkbookRow[]>([
        makeRow(),
        makeRow(),
        makeRow(),
    ]);
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [results, setResults] = useState<BulkReconcileResultRow[] | null>(null);
    const [asyncTaskId, setAsyncTaskId] = useState<string | null>(null);

    const reconcile = useBulkReconcileUsers();
    const { data: groupsData } = useTenantGroups({ limit: 200 });
    const groupNames = useMemo(
        () => (groupsData?.results ?? []).map((g) => g.name).sort(),
        [groupsData],
    );

    const updateRow = (id: string, patch: Partial<WorkbookRow>) => {
        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
    };
    const removeRow = (id: string) => {
        setRows((prev) =>
            prev.length > 1 ? prev.filter((r) => r.id !== id) : prev,
        );
    };
    const addRow = () => setRows((prev) => [...prev, makeRow()]);

    // ---- Derived state -----------------------------------------------------

    const populatedRows = useMemo(
        () => rows.filter((r) => r.email.trim() || r.first_name.trim() || r.last_name.trim()),
        [rows],
    );
    const invalidRows = useMemo(
        () => populatedRows.filter((r) => rowProblems(r).length > 0),
        [populatedRows],
    );
    const validRows = populatedRows.length - invalidRows.length;

    // Counts by category — what would actually happen on submit.
    // The "would invite" is necessarily a guess until the server checks
    // each email against existing users; we just show "active" vs
    // "inactive" rows here.
    const rowCounts = useMemo(() => {
        let active = 0;
        let inactive = 0;
        for (const r of populatedRows) {
            if (rowProblems(r).length > 0) continue;
            if (r.status === "Inactive") inactive++;
            else active++;
        }
        return { active, inactive };
    }, [populatedRows]);

    // ---- Submit handlers --------------------------------------------------

    /** Summarize a 207 result payload as a single toast. */
    const summarizeAndToast = (summary: {
        total: number; created: number; updated: number; unchanged: number; errors: number;
    }) => {
        const parts: string[] = [];
        if (summary.created) parts.push(`${summary.created} created`);
        if (summary.updated) parts.push(`${summary.updated} updated`);
        if (summary.unchanged) parts.push(`${summary.unchanged} unchanged`);
        if (summary.errors) parts.push(`${summary.errors} failed`);
        const desc = parts.join("  •  ");
        if (summary.errors === 0) {
            toast.success(`Reconciled ${summary.total} row${summary.total === 1 ? "" : "s"}`, { description: desc });
        } else if (summary.errors === summary.total) {
            toast.error(`All ${summary.total} rows failed`, { description: desc });
        } else {
            toast.warning(`Reconciled with ${summary.errors} error${summary.errors === 1 ? "" : "s"}`, { description: desc });
        }
    };

    /** Poll an async task until terminal state, then surface results. */
    const pollTaskUntilDone = async (taskId: string) => {
        setAsyncTaskId(taskId);
        // Poll every 1.5s, give up after ~5 min — adjust if needed.
        const start = Date.now();
        while (Date.now() - start < 5 * 60 * 1000) {
            await new Promise((res) => setTimeout(res, 1500));
            try {
                const s = await fetchBulkReconcileStatus(taskId);
                if (s.status === "SUCCESS" && s.result) {
                    setResults(s.result.results);
                    summarizeAndToast(s.result.summary);
                    setAsyncTaskId(null);
                    return;
                }
                if (s.status === "FAILURE") {
                    toast.error(`Job failed: ${s.error ?? "unknown"}`);
                    setAsyncTaskId(null);
                    return;
                }
            } catch (e) {
                // Network blip — keep polling.
                console.warn("status poll failed", e);
            }
        }
        toast.warning(`Job ${taskId} still running — refresh later to see results.`);
        setAsyncTaskId(null);
    };

    const handleSubmitManual = async () => {
        if (populatedRows.length === 0) {
            toast.error("No rows filled in");
            return;
        }
        if (invalidRows.length > 0) {
            toast.error(`${invalidRows.length} row(s) have problems`, {
                description: "Fix highlighted rows before submitting.",
            });
            return;
        }
        setResults(null);
        try {
            const resp = await reconcile.mutateAsync({
                rows: populatedRows.map((r) => ({
                    email: r.email,
                    first_name: r.first_name || undefined,
                    last_name: r.last_name || undefined,
                    group: r.group || undefined,
                    status: r.status,
                    message: r.message || undefined,
                })),
            });
            if ("task_id" in resp && resp.task_id) {
                toast.info(`Queued ${resp.total_rows} rows — polling for completion…`);
                await pollTaskUntilDone(resp.task_id);
            } else if ("summary" in resp && resp.summary) {
                setResults(resp.results);
                summarizeAndToast(resp.summary);
            }
        } catch (e) {
            toast.error("Reconcile failed", {
                description: e instanceof Error ? e.message : undefined,
            });
        }
    };

    const handleSubmitCsv = async () => {
        if (!csvFile) {
            toast.error("Pick a file first");
            return;
        }
        setResults(null);
        try {
            const resp = await reconcile.mutateAsync({ file: csvFile });
            if ("task_id" in resp && resp.task_id) {
                toast.info(`Queued ${resp.total_rows} rows — polling for completion…`);
                await pollTaskUntilDone(resp.task_id);
            } else if ("summary" in resp && resp.summary) {
                setResults(resp.results);
                summarizeAndToast(resp.summary);
            }
        } catch (e) {
            toast.error("Workbook import failed", {
                description: e instanceof Error ? e.message : undefined,
            });
        }
    };

    const { isCopied: allCopied, copyToClipboard: copyAll } = useCopyToClipboard();

    /** Copy every created user's invite link as `email — url` lines so an admin
     *  can hand out access in one go even when invite emails are off. Email is
     *  only known for the manual-entry path (matched by row index); CSV imports
     *  fall back to the bare URL. */
    const handleCopyAllLinks = () => {
        const lines = (results ?? [])
            .filter((r) => r.outcome === "created" && r.invitation_url)
            .map((r) => {
                const email = populatedRows[r.row - 1]?.email;
                return email ? `${email} — ${r.invitation_url}` : (r.invitation_url as string);
            });
        if (lines.length === 0) {
            toast.info("No invite links to copy");
            return;
        }
        copyAll(lines.join("\n"));
        toast.success(`Copied ${lines.length} invite link${lines.length === 1 ? "" : "s"}`);
    };

    const handleDownloadTemplate = () => {
        // Browser navigation to the template endpoint triggers the file
        // download via the Content-Disposition header.
        window.location.href = "/api/User/bulk-reconcile-template/";
    };

    const handleDownloadCurrent = () => {
        // Same endpoint, but populated with the current tenant roster so
        // the admin can edit-and-reupload. Mirrors the Parts CSV export
        // → edit → import workflow.
        window.location.href = "/api/User/bulk-reconcile-template/?populate=true";
    };

    // ---- Render ------------------------------------------------------------

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            {/* Header */}
            <div className="mb-6">
                <Link
                    to="/admin/users"
                    className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
                >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Users
                </Link>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <UserPlus className="h-6 w-6 text-primary" />
                            Bulk User Actions
                        </h1>
                        <p className="text-sm text-muted-foreground mt-1">
                            Add, update, activate, deactivate users in batch — manually or from a workbook.
                            Existing users matched by email; invite resends if already pending.
                        </p>
                    </div>
                    <Button variant="outline" onClick={() => navigate({ to: "/admin/users" })}>
                        Cancel
                    </Button>
                </div>
            </div>

            <Tabs defaultValue="manual" className="w-full">
                <TabsList className="grid w-full max-w-md grid-cols-2">
                    <TabsTrigger value="manual">Manual entry</TabsTrigger>
                    <TabsTrigger value="csv">Upload workbook</TabsTrigger>
                </TabsList>

                {/* ---------- Manual entry tab ---------- */}
                <TabsContent value="manual" className="space-y-4 pt-4">
                    <div className="overflow-x-auto rounded-md border max-h-[70vh] overflow-y-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-muted/50 sticky top-0 z-10">
                                <tr>
                                    <th className="px-3 py-2 text-left font-medium">Email *</th>
                                    <th className="px-3 py-2 text-left font-medium">First name</th>
                                    <th className="px-3 py-2 text-left font-medium">Last name</th>
                                    <th className="px-3 py-2 text-left font-medium min-w-[160px]">Group</th>
                                    <th className="px-3 py-2 text-left font-medium min-w-[120px]">Status</th>
                                    <th className="px-3 py-2 text-left font-medium">Message</th>
                                    <th className="px-3 py-2 w-10"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row) => {
                                    const problems = rowProblems(row);
                                    const populated =
                                        row.email.trim() ||
                                        row.first_name.trim() ||
                                        row.last_name.trim();
                                    const showProblems = populated && problems.length > 0;
                                    return (
                                        <tr
                                            key={row.id}
                                            className={
                                                showProblems
                                                    ? "border-t border-destructive/40 bg-destructive/5"
                                                    : "border-t"
                                            }
                                        >
                                            <td className="px-2 py-1.5">
                                                <Input
                                                    type="email"
                                                    value={row.email}
                                                    onChange={(e) =>
                                                        updateRow(row.id, { email: e.target.value })
                                                    }
                                                    placeholder="person@example.com"
                                                    className="h-8"
                                                />
                                            </td>
                                            <td className="px-2 py-1.5">
                                                <Input
                                                    value={row.first_name}
                                                    onChange={(e) =>
                                                        updateRow(row.id, { first_name: e.target.value })
                                                    }
                                                    placeholder="Ada"
                                                    className="h-8"
                                                />
                                            </td>
                                            <td className="px-2 py-1.5">
                                                <Input
                                                    value={row.last_name}
                                                    onChange={(e) =>
                                                        updateRow(row.id, { last_name: e.target.value })
                                                    }
                                                    placeholder="Lovelace"
                                                    className="h-8"
                                                />
                                            </td>
                                            <td className="px-2 py-1.5">
                                                <Select
                                                    value={row.group}
                                                    onValueChange={(v) => updateRow(row.id, { group: v })}
                                                >
                                                    <SelectTrigger className="h-8">
                                                        <SelectValue placeholder="Pick a group…" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {groupNames.length === 0 && (
                                                            <SelectItem value="__empty__" disabled>
                                                                No groups defined
                                                            </SelectItem>
                                                        )}
                                                        {groupNames.map((g) => (
                                                            <SelectItem key={g} value={g}>
                                                                {g}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </td>
                                            <td className="px-2 py-1.5">
                                                <Select
                                                    value={row.status}
                                                    onValueChange={(v) => updateRow(row.id, { status: v as RowStatus })}
                                                >
                                                    <SelectTrigger className="h-8">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {STATUS_VALUES.map((s) => (
                                                            <SelectItem key={s} value={s}>
                                                                {s}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </td>
                                            <td className="px-2 py-1.5 min-w-[200px]">
                                                <Input
                                                    value={row.message}
                                                    onChange={(e) =>
                                                        updateRow(row.id, { message: e.target.value })
                                                    }
                                                    placeholder="(optional)"
                                                    className="h-8"
                                                />
                                            </td>
                                            <td className="px-2 py-1.5">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                                    onClick={() => removeRow(row.id)}
                                                    disabled={rows.length === 1}
                                                    aria-label="Remove row"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {invalidRows.length > 0 && (
                        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm">
                            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                            <div>
                                <p className="font-medium text-destructive">
                                    {invalidRows.length} row{invalidRows.length === 1 ? "" : "s"} need attention
                                </p>
                                <ul className="mt-1 space-y-0.5 text-muted-foreground text-xs">
                                    {invalidRows.map((r) => (
                                        <li key={r.id}>
                                            {r.email || "(no email)"} — {rowProblems(r).join(", ")}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3">
                        <Button variant="outline" size="sm" onClick={addRow}>
                            <Plus className="h-4 w-4 mr-1.5" />
                            Add row
                        </Button>
                        <div className="flex flex-wrap gap-1.5 text-xs">
                            {rowCounts.active > 0 && (
                                <Badge variant="secondary">{rowCounts.active} active</Badge>
                            )}
                            {rowCounts.inactive > 0 && (
                                <Badge variant="secondary">{rowCounts.inactive} inactive</Badge>
                            )}
                            {invalidRows.length > 0 && (
                                <Badge variant="destructive">{invalidRows.length} need fixing</Badge>
                            )}
                            {populatedRows.length === 0 && (
                                <span className="text-muted-foreground">
                                    Fill in at least one row to enable submit.
                                </span>
                            )}
                        </div>
                        <Button
                            className="ml-auto"
                            disabled={populatedRows.length === 0 || invalidRows.length > 0}
                            onClick={handleSubmitManual}
                        >
                            Apply {validRows > 0 ? `${validRows} ` : ""}row{validRows === 1 ? "" : "s"}
                        </Button>
                    </div>
                </TabsContent>

                {/* ---------- CSV upload tab ---------- */}
                <TabsContent value="csv" className="space-y-4 pt-4">
                    <div className="rounded-md border border-dashed p-10">
                        <div className="flex flex-col items-center gap-3 text-center">
                            <Upload className="h-10 w-10 text-muted-foreground" />
                            <div>
                                <Label
                                    htmlFor="bulk-user-csv"
                                    className="cursor-pointer text-sm font-medium underline underline-offset-4"
                                >
                                    Choose a CSV or Excel workbook
                                </Label>
                                <Input
                                    id="bulk-user-csv"
                                    type="file"
                                    accept=".csv,.xlsx,.xls"
                                    className="hidden"
                                    onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                                />
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Columns: <span className="font-mono">email, first_name, last_name, group, status, message</span>
                                </p>
                                <p className="mt-0.5 text-xs text-muted-foreground">
                                    Status: <span className="font-mono">Active</span> / <span className="font-mono">Inactive</span>. New emails are created &amp; invited; existing emails are reconciled to match the row.
                                </p>
                            </div>
                            {csvFile && (
                                <Badge variant="secondary" className="font-mono text-xs">
                                    {csvFile.name} · {(csvFile.size / 1024).toFixed(1)} KB
                                </Badge>
                            )}
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <Button variant="outline" size="sm" onClick={handleDownloadTemplate}>
                            <Download className="h-4 w-4 mr-1.5" />
                            Empty template
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleDownloadCurrent}>
                            <Download className="h-4 w-4 mr-1.5" />
                            Current users
                        </Button>
                        <p className="text-xs text-muted-foreground">
                            Edit the workbook in Excel then re-upload. Existing users matched by email. ≥25 rows queue in the background.
                        </p>
                        <Button
                            className="ml-auto"
                            disabled={!csvFile}
                            onClick={handleSubmitCsv}
                        >
                            Preview &amp; import
                        </Button>
                    </div>
                </TabsContent>
            </Tabs>

            {/* Per-row results from the last submit */}
            {results && results.length > 0 && (
                <div className="mt-6 rounded-md border overflow-hidden">
                    <div className="px-3 py-2 bg-muted/50 text-sm font-medium flex items-center justify-between gap-2">
                        <span>Results</span>
                        {results.some((r) => r.outcome === "created" && r.invitation_url) && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="h-7"
                                onClick={handleCopyAllLinks}
                            >
                                {allCopied ? (
                                    <Check className="h-3.5 w-3.5 mr-1.5" />
                                ) : (
                                    <LinkIcon className="h-3.5 w-3.5 mr-1.5" />
                                )}
                                Copy all links
                            </Button>
                        )}
                    </div>
                    {results.some((r) => r.outcome === "created" && r.invitation_url) && (
                        <p className="px-3 py-2 border-b bg-muted/20 text-xs text-muted-foreground">
                            Each created user has a signup link below — copy it (or use
                            “Copy all links”) and share it directly. They set their password
                            via that link, so onboarding works even when invite emails aren’t sent.
                        </p>
                    )}
                    <div className="max-h-[40vh] overflow-y-auto">
                        <table className="w-full text-xs">
                            <thead className="bg-muted/30 text-left">
                                <tr>
                                    <th className="px-2 py-1.5 font-medium w-12">Row</th>
                                    <th className="px-2 py-1.5 font-medium w-28">Outcome</th>
                                    <th className="px-2 py-1.5 font-medium">Detail</th>
                                </tr>
                            </thead>
                            <tbody>
                                {results.map((r) => (
                                    <tr key={r.row} className="border-t">
                                        <td className="px-2 py-1.5 text-muted-foreground">{r.row}</td>
                                        <td className="px-2 py-1.5">
                                            <Badge
                                                variant={
                                                    r.outcome === "error"
                                                        ? "destructive"
                                                        : r.outcome === "created"
                                                            ? "default"
                                                            : r.outcome === "updated"
                                                                ? "secondary"
                                                                : "outline"
                                                }
                                                className="text-[10px]"
                                            >
                                                {r.outcome}
                                            </Badge>
                                        </td>
                                        <td className="px-2 py-1.5 text-muted-foreground">
                                            {r.outcome === "error" && r.error}
                                            {r.outcome === "created" && (
                                                <div className="space-y-1">
                                                    <div>
                                                        user created
                                                        {r.warnings?.length ? ` · ${r.warnings.join(", ")}` : ""}
                                                    </div>
                                                    {r.invitation_url && (
                                                        <div className="flex items-center gap-1">
                                                            <code className="truncate max-w-[420px] rounded bg-muted px-1 py-0.5 text-[10px]">
                                                                {r.invitation_url}
                                                            </code>
                                                            <CopyLinkButton url={r.invitation_url} />
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                            {r.outcome === "updated" && (
                                                <>changed: {(r.changes ?? []).join(", ") || "—"}</>
                                            )}
                                            {r.outcome === "unchanged" && "no changes"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {asyncTaskId && (
                <div className="mt-6 rounded-md border bg-muted/30 p-3 text-sm">
                    Polling background job <span className="font-mono">{asyncTaskId}</span>…
                </div>
            )}

            <div className="mt-6 rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground font-mono whitespace-pre-line">
                {`Backend wired:
  • Manual entry → POST /api/User/bulk-reconcile/ with JSON rows
  • Workbook upload → POST /api/User/bulk-reconcile/ multipart with file
  • ≥25 rows → Celery batch with polled status (auto-handled by this page)
  • Per-row results render below on completion

Workbook semantics (state-based, no action column):
  • Email not in tenant      → create user + send invite
  • Email in tenant          → update fields/groups/status to match the row
  • Empty cell               → no change to that field
  • Re-running the same workbook is a no-op once state matches
  • CSV upload: group cells accept semicolon-separated names for multi-group

Resend invitation is NOT here — it's a per-row + bulk-bar action on the
User Management page, not a workbook concern.

Known follow-ups:
  • Invite email \`message\` field is captured in the row but not yet
    threaded into the email template (the row's result emits a warning).`}
            </div>
        </div>
    );
}