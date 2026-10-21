/**
 * Changes to a sampling rule set's rules — added, changed, removed — beside the set's
 * own History. Tightening a plan from every 4th part to every 2nd changes a rule, not
 * the set, so the set's History read "No recorded changes" (user decision 2026-10-20).
 */
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api/generated";
import { RULE_TYPES } from "@/components/sampling/rule-types";

export const ruleSetRuleHistoryOptions = (ruleSetId: string) =>
    queryOptions({
        queryKey: ["record-history", "sampling-rule-set-rules", ruleSetId] as const,
        queryFn: () => api.api_Sampling_rule_sets_rule_history_list({ params: { id: ruleSetId } }),
    });

const show = (v: unknown) => (v == null || v === "" || v === "None" ? "—" : String(v));
const fieldLabel = (f: string) => f.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export function RuleSetRuleHistory({ ruleSetId }: { ruleSetId: string }) {
    const { data } = useQuery({ ...ruleSetRuleHistoryOptions(ruleSetId), enabled: !!ruleSetId });
    const entries = data ?? [];
    if (entries.length === 0) return null;
    return (
        <div className="space-y-2 rounded-md border bg-muted/20 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Rule changes ({entries.length})
            </div>
            <ul className="space-y-2 text-sm">
                {entries.map((e) => {
                    const rule = RULE_TYPES.find((r) => r.value === e.rule_type)?.label ?? e.rule_type ?? "Rule";
                    const changed = Object.entries(e.changes as Record<string, unknown>)
                        .filter(([, v]) => Array.isArray(v) && v.length === 2 && String(v[0]) !== String(v[1]));
                    return (
                        <li key={e.id} className="space-y-0.5">
                            <div className="font-medium">
                                {e.action === "created" ? `Added: ${rule}` : e.action === "removed" ? `Removed: ${rule}` : rule}
                            </div>
                            {e.action === "changed" && changed.map(([f, v]) => {
                                const [from, to] = v as [unknown, unknown];
                                return (
                                    <div key={f} className="flex flex-wrap gap-1">
                                        <span>{fieldLabel(f)}:</span>
                                        <span className="text-muted-foreground line-through">{show(from)}</span>
                                        <span className="text-muted-foreground">→</span>
                                        <span>{show(to)}</span>
                                    </div>
                                );
                            })}
                            <div className="text-xs text-muted-foreground">
                                {e.actor_name || "System"} · {format(new Date(e.timestamp), "PP p")}
                            </div>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
