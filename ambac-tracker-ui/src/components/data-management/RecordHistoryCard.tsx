/**
 * History of one record on its edit page: each revision, what changed from the one
 * before it, who made it and when — plus in-place changes (archiving, a setting that
 * doesn't version) and deletes.
 *
 * A revision is its own row, so the record's audit trail is spread across the ids in
 * its version chain. The chain comes from `version-history`; each revision's audit
 * entries are read, and a revision's changes are its created values against the
 * values the previous revision ended with.
 */
import { useMemo } from "react";
import { queryOptions, useQueries, useQuery } from "@tanstack/react-query";
import { formatDistanceToNowStrict } from "date-fns";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { auditLogOptions } from "@/hooks/useRetrieveAuditLogEntries";
import { useContentTypeMapping } from "@/hooks/useContentTypes";
import { endpointFn } from "@/lib/api/endpoint-fn";
import type { components } from "@/lib/api/generated-types";

type Version = components["schemas"]["VersionSummary"];
type Entry = components["schemas"]["AuditLog"];

const IGNORED = new Set([
    "id", "created_at", "updated_at", "modified_at", "created_by", "version", "previous_version",
    "is_current_version", "identity_id", "identity", "tenant",
]);
const MAX_VERSIONS = 12;

/** auditlog writes "None" for null; blank and null read the same. */
const norm = (v: unknown) => (v === "None" || v === undefined || v === "" ? null : v);
/** Relation managers are logged as their repr, which says nothing. */
const meaningless = (v: unknown) => typeof v === "string" && v.startsWith("<");
const fieldLabel = (f: string) => f.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const show = (v: unknown) => {
    const n = norm(v);
    if (n === null || n === "") return "—";
    const s = String(n);
    return s.length > 40 ? `${s.slice(0, 40)}…` : s;
};

type Change = { field: string; from: unknown; to: unknown };
type Event = {
    key: string; at: string; who: string; kind: "created" | "revision" | "changed" | "deleted";
    version: number; changes: Change[]; reason?: string | null;
    /** The revision before this one left no audit record, so what changed is unknown. */
    unknownBase?: boolean;
};

function pairs(entry: Entry): [string, unknown, unknown][] {
    const raw = entry.changes;
    if (!raw || typeof raw !== "object") return [];
    return Object.entries(raw as Record<string, unknown>)
        .filter(([f, v]) => !IGNORED.has(f) && Array.isArray(v) && v.length === 2)
        .map(([f, v]) => [f, norm((v as unknown[])[0]), norm((v as unknown[])[1])] as [string, unknown, unknown])
        .filter(([, from, to]) => !meaningless(from) && !meaningless(to));
}

/** A versioned row's revision chain, oldest first. */
const versionHistoryOptions = (endpoint: string, id: string) =>
    queryOptions({
        queryKey: ["record-history", endpoint, id] as const,
        queryFn: () => (endpointFn(endpoint, "version_history_list") as (c: unknown) => Promise<Version[]>)({ params: { id } }),
    });

export function RecordHistoryCard({ endpoint, id, model }: {
    /** Route under /api/ (e.g. "Equipment"). */
    endpoint: string;
    id: string;
    /** Content-type model name (e.g. "equipments"). */
    model: string;
}) {
    const { data: versionsData } = useQuery({
        ...versionHistoryOptions(endpoint, id),
        enabled: typeof endpointFn(endpoint, "version_history_list") === "function",
    });
    const versions: Pick<Version, "id" | "version" | "change_description">[] = useMemo(
        () => (versionsData ?? [{ id, version: 1, change_description: null }]).slice(-MAX_VERSIONS),
        [versionsData, id],
    );

    const { getContentTypeId } = useContentTypeMapping();
    const contentType = getContentTypeId(model);
    const entriesByVersion = useQueries({
        queries: versions.map((v) => ({
            ...auditLogOptions({ content_type: contentType, object_pk: String(v.id), ordering: "timestamp", limit: 100 }),
            enabled: contentType !== undefined,
        })),
        combine: (results) => results.map((r) => r.data?.results ?? []),
    });

    const events = useMemo(() => {
        const out: Event[] = [];
        let previousEnd = new Map<string, unknown>();
        versions.forEach((v, i) => {
            const entries = entriesByVersion[i] ?? [];
            const values = new Map<string, unknown>();
            for (const e of entries) {
                const who = e.actor_info?.full_name || e.actor_info?.username || "System";
                const ps = pairs(e);
                if (e.action === 0) {
                    ps.forEach(([f, , to]) => values.set(f, to));
                    const unknownBase = i > 0 && previousEnd.size === 0;
                    const changes = i === 0 || unknownBase
                        ? []
                        : ps.filter(([f, , to]) => previousEnd.has(f) && String(previousEnd.get(f)) !== String(to))
                            .map(([f, , to]) => ({ field: f, from: previousEnd.get(f), to }));
                    out.push({
                        key: `${e.id}`, at: e.timestamp, who, version: v.version,
                        kind: i === 0 ? "created" : "revision", changes, reason: v.change_description, unknownBase,
                    });
                } else if (e.action === 1) {
                    ps.forEach(([f, , to]) => values.set(f, to));
                    const changes = ps.filter(([, from, to]) => String(from) !== String(to))
                        .map(([f, from, to]) => ({ field: f, from, to }));
                    if (changes.length) out.push({ key: `${e.id}`, at: e.timestamp, who, version: v.version, kind: "changed", changes });
                } else if (e.action === 2) {
                    out.push({ key: `${e.id}`, at: e.timestamp, who, version: v.version, kind: "deleted", changes: [] });
                }
            }
            previousEnd = values;
        });
        return out.reverse();
    }, [versions, entriesByVersion]);

    const label: Record<Event["kind"], string> = {
        created: "Created", revision: "New revision", changed: "Changed", deleted: "Deleted",
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">History</CardTitle>
                <CardDescription>
                    {versionsData && versionsData.length > 1
                        ? `${versionsData.length} revisions. Each keeps what it said when it was in force.`
                        : "Every change to this record, newest first."}
                </CardDescription>
            </CardHeader>
            <CardContent>
                {events.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No recorded changes.</p>
                ) : (
                    <ol className="divide-y">
                        {events.map((ev) => (
                            <li key={ev.key} className="flex gap-3 py-3 first:pt-0 last:pb-0">
                                <div className="w-28 shrink-0 space-y-1">
                                    <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label[ev.kind]}</div>
                                    {versionsData && versionsData.length > 1 && (
                                        <Badge variant="outline" className="tabular-nums">rev {ev.version}</Badge>
                                    )}
                                </div>
                                <div className="min-w-0 flex-1 space-y-1 text-sm">
                                    <div className="text-xs text-muted-foreground">
                                        {ev.who} · <span title={new Date(ev.at).toLocaleString()}>{formatDistanceToNowStrict(new Date(ev.at), { addSuffix: true })}</span>
                                    </div>
                                    {ev.reason && <div className="italic">“{ev.reason}”</div>}
                                    {ev.unknownBase && (
                                        <div className="text-xs text-muted-foreground">
                                            The revision before this one predates the audit trail, so what changed isn't known.
                                        </div>
                                    )}
                                    {ev.changes.slice(0, 6).map((c) => (
                                        <div key={c.field} className="flex flex-wrap gap-1">
                                            <span className="font-medium">{fieldLabel(c.field)}:</span>
                                            <span className="text-muted-foreground line-through">{show(c.from)}</span>
                                            <span className="text-muted-foreground">→</span>
                                            <span>{show(c.to)}</span>
                                        </div>
                                    ))}
                                    {ev.changes.length > 6 && (
                                        <div className="text-xs text-muted-foreground">+{ev.changes.length - 6} more</div>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ol>
                )}
            </CardContent>
        </Card>
    );
}
