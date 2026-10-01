/** The master migration workbook — a new plant's data in one .xlsx, a sheet per table.
 *
 * Download the blank workbook, fill in the sheets you need, upload it. The upload is a
 * dry run first: every sheet runs through its table's own import and is rolled back, so
 * the page shows what each row would do and every error before anything is kept. "Load
 * it" runs the same file for real — all or nothing. Re-uploading updates what an
 * earlier load made. See Tracker/services/core/master_workbook.py.
 */
import { useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Check, ChevronDown, ChevronRight, Download, Lock, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/generated";
import type { Schema } from "@/lib/api/types";
import { blobErrorMessage, downloadBlob } from "@/lib/download";
import { getCookie } from "@/lib/utils";

type Result = Schema<"MasterWorkbookResult">;
type SheetResult = Schema<"MasterWorkbookSheetResult">;
type Progress = { current: number; total: number; sheet: string };

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });
const n = (v: number) => v.toLocaleString();

function Panel({ title, aside, children }: { title: string; aside?: React.ReactNode; children: React.ReactNode }) {
    return (
        <section className="overflow-hidden rounded-lg border">
            <div className="flex h-9 items-center justify-between border-b bg-muted/60 px-3">
                <h2 className="text-xs font-semibold uppercase tracking-wider">{title}</h2>
                {aside}
            </div>
            {children}
        </section>
    );
}

function errorDetail(err: unknown, fallback: string) {
    return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;
}

function SheetRow({ sheet }: { sheet: SheetResult }) {
    const noted = sheet.rows.length > 0 || !!sheet.detail;
    const [open, setOpen] = useState(sheet.errors > 0);
    const cell = "w-20 text-right tabular-nums";
    return (
        <>
            <tr className="border-t hover:bg-muted/40">
                <td className="py-1.5 pl-3">
                    {noted ? (
                        <button type="button" onClick={() => setOpen((o) => !o)}
                            className="flex items-center gap-1.5 font-medium hover:underline">
                            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                            {sheet.sheet}
                        </button>
                    ) : (
                        <span className="pl-5 font-medium">{sheet.sheet}</span>
                    )}
                </td>
                <td className={cell}>{sheet.created ? n(sheet.created) : "—"}</td>
                <td className={cell}>{sheet.updated ? n(sheet.updated) : "—"}</td>
                <td className={cell}>{sheet.unchanged ? n(sheet.unchanged) : "—"}</td>
                <td className={`${cell} pr-3`}>
                    {sheet.errors
                        ? <span className="font-semibold text-destructive">{n(sheet.errors)}</span>
                        : <Check className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-label="No errors" />}
                </td>
            </tr>
            {open && noted && (
                <tr>
                    <td colSpan={5} className="bg-muted/30 px-3 pb-2.5 pt-1">
                        {sheet.detail && <p className="py-1 text-sm text-destructive">{sheet.detail}</p>}
                        <ul className="max-h-72 space-y-0.5 overflow-y-auto">
                            {sheet.rows.map((r, i) => (
                                <li key={i} className="flex gap-3 text-sm">
                                    <span className="w-16 shrink-0 tabular-nums text-muted-foreground">Row {r.row}</span>
                                    <span className={r.outcome === "error" ? "text-destructive" : "text-muted-foreground"}>
                                        {r.detail}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </td>
                </tr>
            )}
        </>
    );
}

export default function MasterWorkbookPage() {
    const sheetsQ = useQuery({
        queryKey: ["master-workbook", "sheets"],
        queryFn: () => api.api_MasterWorkbook_sheets_list(),
    });
    const inputRef = useRef<HTMLInputElement>(null);
    const [file, setFile] = useState<File | null>(null);
    // The file the shown result is for: Load runs only the file that was checked.
    const [checked, setChecked] = useState<File | null>(null);
    const [result, setResult] = useState<Result | null>(null);
    const [busy, setBusy] = useState<"check" | "load" | null>(null);
    const [progress, setProgress] = useState<Progress | null>(null);

    const downloadTemplate = async () => {
        try {
            const resp = await api.axios.get("/api/MasterWorkbook/template/", { responseType: "blob" });
            downloadBlob(resp.data, "master_workbook.xlsx");
        } catch (e) {
            toast.error(await blobErrorMessage(e, "Couldn't download the workbook."));
        }
    };

    /** A large workbook runs on a worker: poll it until it's done. */
    const poll = async (taskId: string): Promise<Result> => {
        for (;;) {
            await new Promise((r) => setTimeout(r, 1500));
            const s = await api.api_MasterWorkbook_status_retrieve({ params: { task_id: taskId } });
            if (s.status === "SUCCESS" && s.result) return s.result;
            if (s.status === "FAILURE") throw new Error(s.error || "The run failed.");
            setProgress(s.progress ?? null);
        }
    };

    const run = async (dryRun: boolean) => {
        if (!file) return;
        setBusy(dryRun ? "check" : "load");
        setProgress(null);
        try {
            const form = new FormData();
            form.append("file", file);
            form.append("dry_run", dryRun ? "true" : "false");
            // Not the generated client: a large workbook answers 202 with a task id, a
            // shape the client's single response schema would reject.
            const resp = await api.axios.post("/api/MasterWorkbook/run/", form, { headers: csrf() });
            const body = resp.status === 202 ? await poll(resp.data.task_id) : (resp.data as Result);
            setResult(body);
            setChecked(file);
            if (body.loaded) {
                toast.success(`Loaded: ${n(body.totals.created)} added, ${n(body.totals.updated)} updated.`);
                sheetsQ.refetch();
            } else if (!dryRun) {
                toast.error("Nothing was loaded — fix the errors below and upload it again.");
            }
        } catch (e) {
            toast.error(e instanceof Error && !("response" in e) ? e.message : errorDetail(e, "Couldn't read that workbook."));
        } finally {
            setBusy(null);
            setProgress(null);
        }
    };

    const t = result?.totals;
    const canLoad = !!result && result.dry_run && t?.errors === 0 && checked === file && !busy;

    return (
        <div className="space-y-6 px-8 py-7">
            <div className="space-y-1.5">
                <Link to="/Edit" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="h-3.5 w-3.5" /> Data Management
                </Link>
                <h1 className="text-3xl font-bold tracking-tight">Master workbook</h1>
                <p className="max-w-2xl text-muted-foreground">
                    Load a plant from one spreadsheet: a sheet per table, in load order. Every upload is
                    checked first, and nothing is kept until every row loads.
                </p>
            </div>

            <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
                <div className="flex min-w-0 flex-1 flex-col gap-6">
                    <Panel title="Upload">
                        <div className="flex flex-wrap items-center gap-3 p-3">
                            <Input ref={inputRef} type="file" accept=".xlsx" className="max-w-sm"
                                onChange={(e) => { setFile(e.target.files?.[0] ?? null); }} />
                            <Button onClick={() => run(true)} disabled={!file || !!busy}>
                                <Upload className="mr-1.5 h-4 w-4" />
                                {busy === "check" ? "Checking…" : "Check it"}
                            </Button>
                            <Button variant={canLoad ? "default" : "outline"} onClick={() => run(false)} disabled={!canLoad}
                                title={canLoad ? undefined : "Check the workbook first; it loads once the check finds no errors."}>
                                {busy === "load" ? "Loading…" : "Load it"}
                            </Button>
                        </div>
                        {busy && (
                            <div className="space-y-1.5 border-t px-3 py-2.5">
                                <Progress value={progress ? (progress.current / progress.total) * 100 : 5} />
                                <p className="text-xs text-muted-foreground">
                                    {progress
                                        ? `Sheet ${progress.current} of ${progress.total}: ${progress.sheet}`
                                        : "Reading the workbook…"}
                                </p>
                            </div>
                        )}
                    </Panel>

                    {result && t && (
                        <Panel title={result.loaded ? "Loaded" : result.dry_run ? "Check" : "Not loaded"}
                            aside={result.loaded
                                ? <Badge>Kept</Badge>
                                : <span className="text-xs text-muted-foreground">Nothing has been kept</span>}>
                            <p className="px-3 py-2.5 text-sm">
                                {result.loaded ? "Loaded" : result.dry_run ? "Loading it would add" : "It would have added"}{" "}
                                <strong className="tabular-nums">{n(t.created)}</strong> and update{" "}
                                <strong className="tabular-nums">{n(t.updated)}</strong>
                                {t.unchanged ? <> ({n(t.unchanged)} already up to date)</> : null}.{" "}
                                {t.errors > 0 ? (
                                    <span className="font-medium text-destructive">
                                        {n(t.errors)} row{t.errors === 1 ? "" : "s"} can't load — fix them in the workbook and check it again.
                                    </span>
                                ) : result.dry_run ? (
                                    <span className="font-medium">No errors — it's ready to load.</span>
                                ) : null}
                            </p>
                            {result.ignored_sheets.length > 0 && (
                                <p className="border-t px-3 py-2 text-xs text-muted-foreground">
                                    Not part of the workbook, so not loaded: {result.ignored_sheets.join(", ")}.
                                </p>
                            )}
                            <div className="overflow-x-auto border-t">
                                <table className="w-full text-sm">
                                    <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                                        <tr>
                                            <th className="py-1.5 pl-3 text-left font-medium">Sheet</th>
                                            <th className="w-20 text-right font-medium">New</th>
                                            <th className="w-20 text-right font-medium">Updated</th>
                                            <th className="w-20 text-right font-medium">No change</th>
                                            <th className="w-20 pr-3 text-right font-medium">Errors</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.sheets.map((s) => <SheetRow key={`${checked?.name}-${s.sheet}`} sheet={s} />)}
                                    </tbody>
                                </table>
                            </div>
                        </Panel>
                    )}
                </div>

                <aside className="flex w-full shrink-0 flex-col gap-5 lg:w-80">
                    <Panel title="The workbook"
                        aside={<Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={downloadTemplate}>
                            <Download className="mr-1 h-3.5 w-3.5" /> Download
                        </Button>}>
                        <p className="px-3 pb-1 pt-2.5 text-xs text-muted-foreground">
                            Sheets load in this order; a row may name anything an earlier sheet made. Leave the
                            ones you don't need empty. Processes are built in the process editor first.
                        </p>
                        {sheetsQ.isLoading ? (
                            <Skeleton className="m-3 h-64" />
                        ) : (
                            <ol className="px-3 pb-3">
                                {(sheetsQ.data ?? []).map((s, i) => (
                                    <li key={s.title} className="flex items-start gap-2.5 py-1 text-sm" title={s.about}>
                                        <span className="w-5 pt-0.5 text-[11px] tabular-nums text-muted-foreground">
                                            {String(i + 1).padStart(2, "0")}
                                        </span>
                                        <span className={`flex-1 ${s.allowed ? "" : "text-muted-foreground"}`}>{s.title}</span>
                                        {!s.allowed && (
                                            <Lock className="mt-1 h-3 w-3 text-muted-foreground"
                                                aria-label="You don't have permission to load this sheet" />
                                        )}
                                    </li>
                                ))}
                            </ol>
                        )}
                    </Panel>
                </aside>
            </div>
        </div>
    );
}
