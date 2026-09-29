/**
 * Go-live history — loading records from the system a tenant is leaving, and the
 * one sign-off each load gets. Backend: /api/MigrationBatches/ (viewsets/migration.py,
 * services/core/migration_import.py).
 *
 * A load is create-only and makes one batch. Each batch is verified once, by someone
 * other than the loader; the backend enforces that and its 400 message is surfaced
 * as-is.
 */
import { useState } from "react";
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Download, History, Upload, XCircle } from "lucide-react";

import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";
import { hasEndpoint } from "@/lib/api/endpoint-fn";
import { apiErrorBody } from "@/lib/api-error";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { matchKey } from "@/lib/query-filters";
import { cn } from "@/lib/utils";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

type Batch = components["schemas"]["MigrationBatch"];
type Kind = components["schemas"]["MigrationBatchKindEnum"];

const KIND_LABELS: Record<Kind, string> = {
    TRAINING_RECORDS: "Training records",
    MATERIAL_LOTS: "Material lots",
};

const BATCHES_KEY = "migration-batches";

const batchesOptions = () =>
    queryOptions({
        queryKey: [BATCHES_KEY, "list"] as const,
        // The model orders newest first.
        queryFn: () => api.api_MigrationBatches_list({ queries: { limit: 200 } }),
    });

interface RowResult {
    row: number;
    status: string;
    errors?: string | string[] | Record<string, unknown>;
    warnings?: string[];
}

interface LoadResponse {
    batch: Batch;
    summary: { total: number; created: number; updated: number; errors: number };
    results: RowResult[];
}

/** DRF sends `{detail}`, a bare list (a ValidationError with a string), or field errors. */
function refusalMessage(e: unknown, fallback: string): string {
    const body = apiErrorBody(e);
    if (typeof body === "string" && body) return body;
    if (Array.isArray(body) && body.length) return body.map(String).join(" ");
    if (body && typeof body === "object") {
        const rec = body as Record<string, unknown>;
        if (typeof rec.detail === "string") return rec.detail;
        const parts = Object.values(rec).flatMap((v) => (Array.isArray(v) ? v.map(String) : [String(v)]));
        if (parts.length) return parts.join(" ");
    }
    return fallback;
}

function rowErrorText(errors: RowResult["errors"]): string {
    if (!errors) return "";
    if (typeof errors === "string") return errors;
    if (Array.isArray(errors)) return errors.join(", ");
    return Object.entries(errors)
        .map(([field, msg]) => `${field}: ${Array.isArray(msg) ? msg.join(", ") : String(msg)}`)
        .join(", ");
}

const when = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString() : "");

export function GoLiveHistoryPage() {
    const { has, isLoading: permsLoading } = usePermissionSet();
    const { data: user } = useAuthUser();
    const isStaff = user?.is_staff ?? false;

    const endpointExists = hasEndpoint("MigrationBatches", "list");
    const canView = isStaff || has("view_migrationbatch");
    const canLoad = hasEndpoint("MigrationBatches", "import_create") && (isStaff || has("add_migrationbatch"));
    const canVerify = hasEndpoint("MigrationBatches", "verify_create") && (isStaff || has("change_migrationbatch"));

    const { data: page, isLoading } = useQuery({ ...batchesOptions(), enabled: endpointExists && canView });
    const batches: Batch[] = page?.results ?? [];

    const [verifying, setVerifying] = useState<Batch | null>(null);

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-4">
            <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
                <History className="h-6 w-6 text-muted-foreground" /> Go-live history
            </h1>

            <p className="text-sm text-muted-foreground">
                At go-live, history from the old system is loaded here rather than re-keyed.{" "}
                <b className="text-foreground">Training records</b> count toward qualification
                immediately, so each must name where the original lives
                (<code className="text-xs">source_reference</code>).{" "}
                <b className="text-foreground">Material lots</b> that carry traceability (a supplier
                lot or cert reference, plus an expiry where the material has a shelf life) arrive
                accepted; lots without it arrive in quarantine. Each load is one batch, and someone{" "}
                <b className="text-foreground">other than the loader</b> verifies it once, after
                checking it against the source.
            </p>

            {!endpointExists ? (
                <p className="text-sm text-muted-foreground">
                    This server doesn't offer go-live loads.
                </p>
            ) : !permsLoading && !canView ? (
                <p className="text-sm text-muted-foreground">
                    You don't have permission to view go-live loads.
                </p>
            ) : (
                <>
                    {canLoad && <LoadCard />}

                    <div className="overflow-x-auto rounded-md border">
                        <table className="w-full text-sm">
                            <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                                <tr>
                                    <th className="px-3 py-2">Kind</th>
                                    <th className="px-3 py-2">Source system</th>
                                    <th className="px-3 py-2 text-right">Rows</th>
                                    <th className="px-3 py-2">Loaded</th>
                                    <th className="px-3 py-2">Verified</th>
                                    <th className="w-24 px-3 py-2"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {isLoading && (
                                    <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">Loading…</td></tr>
                                )}
                                {!isLoading && batches.length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                                        No history has been loaded yet.
                                    </td></tr>
                                )}
                                {batches.map((b) => (
                                    <tr key={b.id} className="border-t align-top">
                                        <td className="px-3 py-2">
                                            <Badge variant="outline">{KIND_LABELS[b.kind] ?? b.kind}</Badge>
                                        </td>
                                        <td className="px-3 py-2">
                                            <div className="font-medium">{b.source_system}</div>
                                            {b.notes && <div className="text-xs text-muted-foreground">{b.notes}</div>}
                                        </td>
                                        <td className="px-3 py-2 text-right tabular-nums">{b.row_count}</td>
                                        <td className="px-3 py-2">
                                            <div>{b.imported_by_email}</div>
                                            <div className="text-xs text-muted-foreground">{when(b.created_at)}</div>
                                        </td>
                                        <td className="px-3 py-2">
                                            {b.is_verified ? (
                                                <>
                                                    <div>{b.verified_by_email ?? "—"}</div>
                                                    <div className="text-xs text-muted-foreground">{when(b.verified_at)}</div>
                                                    {b.verification_notes && (
                                                        <div className="text-xs text-muted-foreground">{b.verification_notes}</div>
                                                    )}
                                                </>
                                            ) : (
                                                <Badge variant="secondary">Not verified</Badge>
                                            )}
                                        </td>
                                        <td className="px-3 py-2 text-right">
                                            {!b.is_verified && canVerify && (
                                                <Button size="sm" variant="outline" onClick={() => setVerifying(b)}>
                                                    Verify
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            <VerifyDialog batch={verifying} onClose={() => setVerifying(null)} />
        </div>
    );
}

function LoadCard() {
    const qc = useQueryClient();
    const [kind, setKind] = useState<Kind>("TRAINING_RECORDS");
    const [sourceSystem, setSourceSystem] = useState("");
    const [notes, setNotes] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [fileInputKey, setFileInputKey] = useState(0);
    const [result, setResult] = useState<LoadResponse | null>(null);

    const template = useMutation({
        mutationFn: async (k: Kind) => {
            const response = await api.axios.get("/api/MigrationBatches/template/", {
                params: { kind: k }, responseType: "blob",
            });
            return response.data as Blob;
        },
        onSuccess: (blob, k) => downloadBlob(blob, `${k.toLowerCase()}_migration.csv`),
        onError: async (e) => toast.error(await blobErrorMessage(e, "Couldn't download the template.")),
    });

    const load = useMutation({
        mutationFn: async () => {
            const form = new FormData();
            form.append("file", file!);
            form.append("kind", kind);
            form.append("source_system", sourceSystem.trim());
            if (notes.trim()) form.append("notes", notes.trim());
            const response = await api.axios.post("/api/MigrationBatches/import/", form, {
                headers: { "Content-Type": "multipart/form-data" },
                validateStatus: (s) => (s >= 200 && s < 300) || s === 207,
            });
            return response.data as LoadResponse;
        },
        onSuccess: (data) => {
            setResult(data);
            qc.invalidateQueries(matchKey([BATCHES_KEY]));
            const { created, errors } = data.summary;
            if (errors === 0) toast.success(`Loaded ${created} row${created === 1 ? "" : "s"}.`);
            else toast.warning(`Loaded ${created}; ${errors} row${errors === 1 ? "" : "s"} refused.`);
            setFile(null);
            setFileInputKey((n) => n + 1);
        },
        onError: (e) => toast.error(refusalMessage(e, "Couldn't load the file.")),
    });

    const ready = !!file && sourceSystem.trim().length > 0 && !load.isPending;
    const errorRows = result?.results.filter((r) => r.status === "error") ?? [];
    const warnedRows = result?.results.filter((r) => r.status !== "error" && (r.warnings?.length ?? 0) > 0) ?? [];

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Load history</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="golive-kind">What it is</Label>
                        <Select value={kind} onValueChange={(v) => setKind(v as Kind)}>
                            <SelectTrigger id="golive-kind"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {(Object.keys(KIND_LABELS) as Kind[]).map((k) => (
                                    <SelectItem key={k} value={k}>{KIND_LABELS[k]}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Button
                            type="button"
                            variant="link"
                            size="sm"
                            className="h-auto px-0"
                            onClick={() => template.mutate(kind)}
                            disabled={template.isPending}
                        >
                            <Download className="mr-1 h-3.5 w-3.5" /> Download template
                        </Button>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="golive-source">Source system (required)</Label>
                        <Input
                            id="golive-source"
                            placeholder="e.g. Legacy HR — Workday"
                            value={sourceSystem}
                            onChange={(e) => setSourceSystem(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="golive-notes">Notes</Label>
                        <Textarea
                            id="golive-notes"
                            rows={2}
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="golive-file">File (.csv or .xlsx)</Label>
                        <Input
                            key={fileInputKey}
                            id="golive-file"
                            type="file"
                            accept=".csv,.xlsx"
                            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                        />
                    </div>
                </div>
                <div className="flex justify-end">
                    <Button onClick={() => load.mutate()} disabled={!ready}>
                        <Upload className="mr-1 h-4 w-4" /> {load.isPending ? "Loading…" : "Load"}
                    </Button>
                </div>

                {result && (
                    <div className="space-y-3 border-t pt-4">
                        <p className="text-sm text-muted-foreground">
                            {KIND_LABELS[result.batch.kind]} from {result.batch.source_system}: batch
                            of {result.batch.row_count} row{result.batch.row_count === 1 ? "" : "s"}, awaiting
                            verification by someone else.
                        </p>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            <SummaryCard label="Total" value={result.summary.total} variant="default" />
                            <SummaryCard label="Created" value={result.summary.created} variant="success" />
                            <SummaryCard label="Updated" value={result.summary.updated} variant="info" />
                            <SummaryCard label="Errors" value={result.summary.errors} variant="error" />
                        </div>
                        {errorRows.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium">Errors ({errorRows.length})</p>
                                <div className="max-h-64 space-y-1 overflow-y-auto">
                                    {errorRows.map((r) => (
                                        <div key={`e-${r.row}`} className="flex items-start gap-2 rounded bg-muted/50 p-2 text-sm">
                                            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                                            <div className="min-w-0">
                                                <span className="font-medium">Row {r.row}</span>
                                                <p className="text-xs text-red-600 dark:text-red-400">{rowErrorText(r.errors)}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {warnedRows.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-sm font-medium">Check these rows ({warnedRows.length})</p>
                                <div className="max-h-64 space-y-1 overflow-y-auto">
                                    {warnedRows.map((r) => (
                                        <div key={`w-${r.row}`} className="rounded bg-amber-50 p-2 text-xs dark:bg-amber-950/30">
                                            <span className="font-medium">Row {r.row}:</span> {r.warnings!.join("; ")}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {errorRows.length === 0 && warnedRows.length === 0 && (
                            <p className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
                                <CheckCircle2 className="h-4 w-4" /> Every row loaded as written.
                            </p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function VerifyDialog({ batch, onClose }: { batch: Batch | null; onClose: () => void }) {
    const qc = useQueryClient();
    const [notes, setNotes] = useState("");

    const verify = useMutation({
        mutationFn: (b: Batch) =>
            api.api_MigrationBatches_verify_create(
                notes.trim() ? { notes: notes.trim() } : {},
                { params: { id: b.id } },
            ),
        onSuccess: () => {
            toast.success("Batch verified.");
            qc.invalidateQueries(matchKey([BATCHES_KEY]));
            setNotes("");
            onClose();
        },
        onError: (e) => toast.error(refusalMessage(e, "Couldn't verify the batch.")),
    });

    return (
        <Dialog open={!!batch} onOpenChange={(o) => { if (!o) { setNotes(""); onClose(); } }}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Verify batch</DialogTitle>
                    <DialogDescription>
                        {batch && (
                            <>
                                {KIND_LABELS[batch.kind]} from {batch.source_system}, {batch.row_count} rows,
                                loaded by {batch.imported_by_email}. Verify only after checking it against
                                the source. This is recorded once and can't be undone.
                            </>
                        )}
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-1.5">
                    <Label htmlFor="golive-verify-notes">What you checked</Label>
                    <Textarea
                        id="golive-verify-notes"
                        rows={3}
                        placeholder="e.g. quantities match the go-live count; sampled 10 records against the originals"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                    />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>Cancel</Button>
                    <Button onClick={() => batch && verify.mutate(batch)} disabled={verify.isPending}>
                        {verify.isPending ? "Verifying…" : "Verify"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function SummaryCard({
    label, value, variant,
}: { label: string; value: number; variant: "default" | "success" | "info" | "error" }) {
    const styles = {
        default: "bg-muted",
        success: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300",
        info: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
        error: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
    };
    return (
        <div className={cn("rounded-lg p-2 text-center", styles[variant])}>
            <div className="text-xl font-bold">{value}</div>
            <div className="text-xs">{label}</div>
        </div>
    );
}
