/**
 * Supervisor training overrides across parts, for a period: each time someone worked a
 * step without the required training because a supervisor authorised it — who, for whom,
 * on which step and part, why, and what training was missing. For QA and auditors
 * (`view_auditlog`); the same override shows one part at a time on that part's steps.
 */
import { useState } from "react";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

const isoDay = (d: Date) => format(d, "yyyy-MM-dd");

const trainingOverridesOptions = (since: string, until: string) =>
    queryOptions({
        queryKey: ["training-overrides", { since, until }] as const,
        queryFn: () => api.api_StepExecutions_training_overrides_list({ queries: { since, until } }),
    });

export function TrainingOverridesPage() {
    const canReview = usePermissionSet().has("view_auditlog");
    const [since, setSince] = useState(() => isoDay(new Date(Date.now() - 30 * 86400000)));
    const [until, setUntil] = useState(() => isoDay(new Date()));
    const { data, isLoading, error } = useQuery({
        ...trainingOverridesOptions(since, until),
        enabled: canReview && !!since && !!until,
    });
    const [flaggedOnly, setFlaggedOnly] = useState(false);
    const all = data ?? [];
    const flaggedCount = all.filter((r) => r.flagged).length;
    const rows = flaggedOnly ? all.filter((r) => r.flagged) : all;

    return (
        <div className="mx-auto max-w-6xl space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-semibold">Training overrides</h1>
                <p className="text-sm text-muted-foreground">
                    Steps a supervisor let someone work without the required training, newest first.
                </p>
            </div>

            {!canReview ? (
                <p className="text-sm text-muted-foreground">
                    Reviewing overrides across parts needs the audit-log permission (QA Manager, Auditor,
                    Document Controller, Tenant Admin). An override on one part shows on that part&rsquo;s steps.
                </p>
            ) : (
                <>
                    <div className="flex flex-wrap items-end gap-4">
                        <div className="space-y-1">
                            <Label htmlFor="tov-since">From</Label>
                            <Input id="tov-since" type="date" value={since} onChange={(e) => setSince(e.target.value)} />
                        </div>
                        <div className="space-y-1">
                            <Label htmlFor="tov-until">To</Label>
                            <Input id="tov-until" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
                        </div>
                        <div className="pb-2 text-sm text-muted-foreground">
                            {isLoading ? "Loading…" : `${all.length} override${all.length === 1 ? "" : "s"}`}
                        </div>
                        {/* An override flagged as given wrongly is what QA looks at first. */}
                        <label className="flex items-center gap-2 pb-2 text-sm">
                            <input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} />
                            Flagged for review only ({flaggedCount})
                        </label>
                    </div>

                    {error ? (
                        <p className="text-sm text-destructive">{apiErrorMessage(error) ?? "Couldn't load the overrides."}</p>
                    ) : rows.length === 0 ? (
                        <p className="text-sm text-muted-foreground">{isLoading ? "" : "No overrides in this period."}</p>
                    ) : (
                        <div className="overflow-x-auto rounded-md border">
                            <table className="w-full text-sm">
                                <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
                                    <tr>
                                        <th className="p-2">When</th>
                                        <th className="p-2">Worked by</th>
                                        <th className="p-2">Authorised by</th>
                                        <th className="p-2">Step</th>
                                        <th className="p-2">Part</th>
                                        <th className="p-2">Missing training</th>
                                        <th className="p-2">Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.map((r) => (
                                        <tr key={r.execution_id} className="border-t align-top">
                                            <td className="whitespace-nowrap p-2 text-xs tabular-nums">
                                                {r.at ? format(new Date(r.at), "PP p") : "—"}
                                            </td>
                                            <td className="p-2">{r.worker_name || "—"}</td>
                                            <td className="p-2">{r.authorized_by_name || "—"}</td>
                                            <td className="p-2">
                                                {r.step_name}
                                                {r.visit_number > 1 && <span className="text-xs text-muted-foreground"> (visit {r.visit_number})</span>}
                                            </td>
                                            <td className="p-2">
                                                <div className="font-mono text-xs">{r.part_erp_id}</div>
                                                {r.work_order_erp_id && <div className="text-xs text-muted-foreground">{r.work_order_erp_id}</div>}
                                            </td>
                                            <td className="p-2">
                                                <div className="flex flex-wrap gap-1">
                                                    {r.missing_training.length
                                                        ? r.missing_training.map((t) => <Badge key={t} variant="outline">{t}</Badge>)
                                                        : <span className="text-xs text-muted-foreground">—</span>}
                                                </div>
                                            </td>
                                            <td className="p-2">
                                                <span className="italic">{r.reason ? `“${r.reason}”` : "—"}</span>
                                                {r.flagged && (
                                                    <div className="mt-1 text-xs text-amber-700">
                                                        <Badge variant="outline" className="mr-1 border-amber-500 text-amber-700">Flagged</Badge>
                                                        {r.flagged_by_name}{r.flag_reason ? `: “${r.flag_reason}”` : ""}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
