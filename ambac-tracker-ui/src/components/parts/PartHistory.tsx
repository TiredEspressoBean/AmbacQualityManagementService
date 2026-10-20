/**
 * A serial's history: the audit trail of the part AND of every record about it — step
 * executions, measurements, material draws, quality reports, dispositions, overrides —
 * as one timeline (GET /api/Parts/{id}/history/, derived on read from django-auditlog).
 *
 * The generic AuditTrail shows one object's last five changes, which for a part is little
 * more than its step moving; the work done to it lives on other records.
 */
import { useState } from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/generated";
import { useContentTypeMapping } from "@/hooks/useContentTypes";
import { CorrectionReasons } from "@/components/audit/CorrectionReasons";

const PAGE = 25;

const partHistoryOptions = (partId: string, limit: number) =>
    queryOptions({
        queryKey: ["part-history", partId, limit],
        queryFn: () => api.api_Parts_history_retrieve({ params: { id: partId }, queries: { limit } }),
    });

const DOT: Record<string, string> = {
    created: "bg-green-100 border-green-500",
    updated: "bg-blue-100 border-blue-500",
    deleted: "bg-red-100 border-red-500",
};

type Props = { objectId: string | number; modelType?: string };

export function PartHistory({ objectId }: Props) {
    const [limit, setLimit] = useState(PAGE);
    const { data, isLoading, error, isFetching } = useQuery({
        ...partHistoryOptions(String(objectId), limit),
        placeholderData: (prev) => prev,
    });
    const partContentType = useContentTypeMapping().getContentTypeId("parts");
    const corrections = <CorrectionReasons contentType={partContentType} objectId={String(objectId)} />;

    if (isLoading) return <p className="text-sm text-muted-foreground">Loading history…</p>;
    if (error) return <p className="text-sm text-destructive">Couldn&rsquo;t load this part&rsquo;s history.</p>;

    const entries = data?.results ?? [];
    if (entries.length === 0) {
        return (
            <div className="space-y-4">
                {corrections}
                <p className="text-sm text-muted-foreground">
                    No recorded history. The audit log records changes as work happens, so records
                    loaded in their final state (an import, the demo data) start with none.
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {corrections}
            <ol className="space-y-4">
                {entries.map((e, i) => (
                    <li key={e.id} className="flex gap-3">
                        <div className="flex flex-col items-center pt-1">
                            <span className={`h-3 w-3 rounded-full border-2 ${DOT[e.action] ?? "bg-muted border-muted-foreground"}`} />
                            {i < entries.length - 1 && <span className="mt-1 w-px flex-1 bg-border" />}
                        </div>
                        <div className="min-w-0 flex-1 pb-1">
                            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                                <p className="text-sm">
                                    <span className="font-medium capitalize">{e.record_type}</span>{" "}
                                    <span className="text-muted-foreground">{e.action}</span>
                                    {" · "}
                                    <span className="font-medium">{e.actor_name || "System"}</span>
                                </p>
                                <time
                                    dateTime={e.timestamp}
                                    title={formatDistanceToNow(new Date(e.timestamp), { addSuffix: true })}
                                    className="text-xs text-muted-foreground tabular-nums whitespace-nowrap"
                                >
                                    {format(new Date(e.timestamp), "PP p")}
                                </time>
                            </div>
                            <p className="truncate text-xs text-muted-foreground" title={e.record}>{e.record}</p>
                            {e.changes.length > 0 && (
                                <ul className="mt-1 space-y-0.5 text-sm">
                                    {e.changes.slice(0, 6).map((c) => (
                                        <li key={c.field} className="break-words">
                                            <span className="font-medium capitalize">{c.field}:</span>{" "}
                                            <span className="text-muted-foreground">
                                                {e.action === "created" || c.old == null
                                                    ? (c.new ?? "—")
                                                    : `${c.old} → ${c.new ?? "—"}`}
                                            </span>
                                        </li>
                                    ))}
                                    {e.changes.length > 6 && (
                                        <li className="text-xs text-muted-foreground">
                                            +{e.changes.length - 6} more field{e.changes.length - 6 === 1 ? "" : "s"}
                                        </li>
                                    )}
                                </ul>
                            )}
                        </div>
                    </li>
                ))}
            </ol>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="tabular-nums">{entries.length} of {data?.count ?? entries.length}</span>
                {(data?.count ?? 0) > entries.length && (
                    <Button variant="outline" size="sm" disabled={isFetching} onClick={() => setLimit((n) => n + PAGE)}>
                        {isFetching ? "Loading…" : "Show older"}
                    </Button>
                )}
            </div>
        </div>
    );
}

export default PartHistory;
