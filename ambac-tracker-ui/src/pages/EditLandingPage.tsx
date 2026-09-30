// src/pages/EditLandingPage.tsx — Data Management: every shared-config table, the
// way the Django admin index lists them. The tables and their parent/child shape
// live in lib/data-management/tables.ts.
import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQueries } from "@tanstack/react-query";
import { formatDistanceToNowStrict } from "date-fns";
import { Check, CornerDownRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { DataExportMenu } from "@/components/data-export-menu";
import { DataImportDialog } from "@/components/data-import-dialog";
import { endpointFn, hasEndpoint } from "@/lib/api/endpoint-fn";
import { matchKey } from "@/lib/query-filters";
import { useQueryClient } from "@tanstack/react-query";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { useRetrieveAuditLogEntries } from "@/hooks/useRetrieveAuditLogEntries";
import { ALL_TABLES, DATA_MANAGEMENT, LOAD_ORDER, type DMTable } from "@/lib/data-management/tables";

const ACTION_LABEL: Record<number, string> = { 0: "Added", 1: "Changed", 2: "Deleted", 3: "Viewed" };

/** Row count for one table: a one-row page of its list, read for `count`. */
function countQuery(t: DMTable, enabled: boolean) {
    return {
        queryKey: ["data-management", "count", t.endpoint, t.countQuery ?? null] as const,
        queryFn: async () => {
            const list = endpointFn(t.endpoint, "list");
            if (typeof list !== "function") return null;
            // Paginated lists carry `count`; an unpaginated one (milestone templates) is the rows.
            const page = await list({ queries: { limit: 1, ...(t.countQuery ?? {}) } }) as { count?: number } | unknown[];
            return Array.isArray(page) ? page.length : page?.count ?? null;
        },
        enabled,
        staleTime: 60_000,
        retry: false,
    };
}

function TableRow({ table, count, canAdd, child, invalidate }: {
    table: DMTable; count: number | null | undefined; canAdd: boolean; child?: boolean;
    invalidate: () => void;
}) {
    // A table that is a slice of another endpoint (receiving plans are steps) can't
    // import through it: the file would land as rows of the whole endpoint.
    const canImport = canAdd && !table.slice && hasEndpoint(table.endpoint, "import_create");
    const canExport = hasEndpoint(table.endpoint, "export_retrieve");
    const actionLink = "h-auto px-0 text-[13px] font-normal text-muted-foreground hover:text-foreground";
    return (
        <div className="flex min-h-10 items-center gap-2.5 border-t px-3 py-1.5 text-sm first:border-t-0 hover:bg-muted/40">
            <div className="flex min-w-0 flex-1 items-center gap-1.5">
                {child && <CornerDownRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />}
                {table.list ? (
                    <Link to={table.list} className="truncate font-medium hover:underline">{table.name}</Link>
                ) : (
                    <span className="truncate font-medium">{table.name}</span>
                )}
                {table.versioned && (
                    <span title="Edits create a new revision"
                        className="shrink-0 rounded border px-1 text-[11px] leading-4 text-muted-foreground">rev</span>
                )}
                {table.editedOn && (
                    <span className="hidden truncate text-xs text-muted-foreground xl:inline">on {table.editedOn}</span>
                )}
            </div>
            <span className="w-12 text-right text-xs tabular-nums text-muted-foreground">
                {count == null ? "" : count.toLocaleString()}
            </span>
            <span className="w-7">
                {table.add && canAdd && (
                    <Link to={table.add} search={table.addSearch as never}
                        className="text-[13px] text-muted-foreground hover:text-foreground hover:underline">Add</Link>
                )}
            </span>
            <span className="w-11">
                {canImport && (
                    <DataImportDialog
                        modelName={table.endpoint}
                        displayName={table.name}
                        onImportComplete={invalidate}
                        trigger={<Button variant="link" className={actionLink}>Import</Button>}
                    />
                )}
            </span>
            <span className="w-11">
                {canExport && (
                    <DataExportMenu
                        modelName={table.endpoint}
                        showTemplateOption={hasEndpoint(table.endpoint, "import_template_retrieve")}
                        {...(table.countQuery ? { queryParams: table.countQuery } : {})}
                        trigger={<Button variant="link" className={actionLink}>Export</Button>}
                    />
                )}
            </span>
        </div>
    );
}

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

export default function EditLandingPage() {
    const queryClient = useQueryClient();
    const { has, isLoading: permsLoading } = usePermissionSet();
    const { data: authUser } = useAuthUser();
    const isStaff = (authUser as { is_staff?: boolean } | undefined)?.is_staff ?? false;
    const allows = (codename: string) => isStaff || has(codename);
    const [q, setQ] = useState("");

    const visible = useMemo(
        () => (permsLoading ? [] : ALL_TABLES.filter((t) => allows(`view_${t.model}`))),
        // eslint-disable-next-line react-hooks/exhaustive-deps -- `allows` follows the permission load
        [permsLoading, isStaff, has],
    );
    const visibleKeys = useMemo(() => new Set(visible.map((t) => t.key)), [visible]);

    const counts = useQueries({
        queries: ALL_TABLES.map((t) => countQuery(t, visibleKeys.has(t.key))),
        combine: (results) => results.map((r) => r.data),
    });
    const countByKey = useMemo(
        () => new Map(ALL_TABLES.map((t, i) => [t.key, counts[i]])),
        [counts],
    );

    const canSeeAudit = allows("view_logentry") || allows("view_auditlog");
    const { data: recent } = useRetrieveAuditLogEntries(
        { limit: 8, ordering: "-timestamp" }, undefined, { enabled: !permsLoading && canSeeAudit },
    );

    const needle = q.trim().toLowerCase();
    const groups = DATA_MANAGEMENT.map((g) => ({
        title: g.title,
        tables: g.tables
            .filter((t) => visibleKeys.has(t.key) || (t.children ?? []).some((c) => visibleKeys.has(c.key)))
            .map((t) => ({
                ...t,
                children: (t.children ?? []).filter((c) => visibleKeys.has(c.key)),
            }))
            .filter((t) => !needle
                || t.name.toLowerCase().includes(needle)
                || t.children.some((c) => c.name.toLowerCase().includes(needle))),
    })).filter((g) => g.tables.length > 0);

    // Two columns balanced by row count, keeping each group whole.
    const columns = useMemo(() => {
        const cols: typeof groups[] = [[], []];
        const size = [0, 0];
        for (const g of groups) {
            const rows = g.tables.reduce((n, t) => n + 1 + t.children.length, 0) + 1;
            const i = size[0] <= size[1] ? 0 : 1;
            cols[i].push(g);
            size[i] += rows;
        }
        return cols.filter((c) => c.length);
    }, [groups]);

    const invalidateFor = (t: DMTable) => () => {
        queryClient.invalidateQueries(matchKey(["data-management", "count", t.endpoint]));
    };

    const loadSteps = LOAD_ORDER.filter((s) => visibleKeys.has(s.key)).map((s) => ({
        ...s,
        table: ALL_TABLES.find((t) => t.key === s.key),
        done: (countByKey.get(s.key) ?? 0) > 0,
    }));

    return (
        <div className="space-y-7 px-8 py-7">
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="space-y-1.5">
                    <p className="text-sm text-muted-foreground">Admin</p>
                    <h1 className="text-3xl font-bold tracking-tight">Data Management</h1>
                    <p className="text-muted-foreground">
                        Every shared table the plant is set up with — to browse, add, correct, archive and bulk-load.
                    </p>
                </div>
                <label className="flex w-full max-w-xs flex-col gap-1.5">
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Find a table</span>
                    <Input type="search" placeholder="Part types, shifts, users…" value={q} onChange={(e) => setQ(e.target.value)} />
                </label>
            </div>

            <div className="flex flex-col gap-7 lg:flex-row lg:items-start">
                <div className="flex min-w-0 flex-1 flex-col gap-5 xl:flex-row xl:items-start">
                    {permsLoading ? (
                        <Skeleton className="h-96 w-full" />
                    ) : columns.length === 0 ? (
                        <div className="flex-1 rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
                            {needle ? "No table matches that." : "You don't have access to any tables here."}
                        </div>
                    ) : columns.map((col, i) => (
                        <div key={i} className="flex min-w-0 flex-1 flex-col gap-5">
                            {col.map((g) => (
                                <Panel key={g.title} title={g.title}
                                    aside={<span className="text-xs text-muted-foreground">{g.tables.length} tables</span>}>
                                    {g.tables.map((t) => (
                                        <div key={t.key}>
                                            {visibleKeys.has(t.key) && (
                                                <TableRow table={t} count={countByKey.get(t.key)}
                                                    canAdd={allows(`add_${t.model}`)} invalidate={invalidateFor(t)} />
                                            )}
                                            {t.children.map((c) => (
                                                <TableRow key={c.key} table={c} child count={countByKey.get(c.key)}
                                                    canAdd={allows(`add_${c.model}`)} invalidate={invalidateFor(c)} />
                                            ))}
                                        </div>
                                    ))}
                                </Panel>
                            ))}
                        </div>
                    ))}
                </div>

                <aside className="flex w-full shrink-0 flex-col gap-5 lg:w-72">
                    {canSeeAudit && (
                        <Panel title="Recent changes"
                            aside={<Link to="/admin/audit-log" className="text-xs text-muted-foreground hover:underline">Audit log</Link>}>
                            {(recent?.results ?? []).length === 0 ? (
                                <p className="p-3 text-sm text-muted-foreground">Nothing yet.</p>
                            ) : (recent?.results ?? []).map((e) => (
                                <div key={e.id} className="flex gap-2.5 border-t px-3 py-2 first:border-t-0">
                                    <span className="w-14 shrink-0 pt-0.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                                        {ACTION_LABEL[e.action] ?? "Changed"}
                                    </span>
                                    <span className="flex min-w-0 flex-col gap-0.5">
                                        <span className="truncate text-sm font-medium">{e.object_repr}</span>
                                        <span className="truncate text-xs text-muted-foreground">
                                            {e.content_type_name} · {e.actor_info?.full_name || e.actor_info?.username || "System"} · {formatDistanceToNowStrict(new Date(e.timestamp), { addSuffix: true })}
                                        </span>
                                    </span>
                                </div>
                            ))}
                        </Panel>
                    )}

                    {loadSteps.length > 0 && (
                        <Panel title="Load order"
                            aside={<span className="text-xs tabular-nums text-muted-foreground">
                                {loadSteps.filter((s) => s.done).length}/{loadSteps.length}
                            </span>}>
                            <p className="px-3 pb-1 pt-2.5 text-xs text-muted-foreground">
                                Import in this order when loading a plant; later tables point at earlier ones.
                            </p>
                            <ol className="px-3 pb-3">
                                {loadSteps.map((s, i) => (
                                    <li key={s.key} className="flex h-7 items-center gap-2.5 text-sm">
                                        <span className="w-5 text-[11px] tabular-nums text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
                                        {s.table?.list ? (
                                            <Link to={s.table.list} className={`flex-1 hover:underline ${s.done ? "" : "text-muted-foreground"}`}>{s.label}</Link>
                                        ) : (
                                            <span className="flex-1">{s.label}</span>
                                        )}
                                        {s.done
                                            ? <Check className="h-3.5 w-3.5" aria-label="Has data" />
                                            : <span className="text-[11px] text-muted-foreground">empty</span>}
                                    </li>
                                ))}
                            </ol>
                        </Panel>
                    )}
                </aside>
            </div>
        </div>
    );
}
