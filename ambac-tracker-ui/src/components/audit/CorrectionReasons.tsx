/**
 * Corrections made to one record, each with the reason given for it (RecordEdit):
 * field · old → new · reason, who and when. Shown inside a record's History so the
 * "why" sits beside the "what". Renders nothing when the record has no corrections.
 */
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api/generated";
import { HOLD_LABELS } from "@/components/receiving/lotStatus";

export const recordCorrectionsOptions = (contentType: number, objectId: string) =>
    queryOptions({
        queryKey: ["record-edits", contentType, objectId] as const,
        queryFn: () => api.api_RecordEdits_list({ queries: { content_type: contentType, object_id: objectId } }),
    });

const fieldLabel = (f: string) => f.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
/** Fields whose change is a decision, with how each stored value reads. */
const DECISION_FIELD_LABELS: Record<string, Record<string, string>> = {
    priority: { "1": "Urgent", "2": "High", "3": "Normal", "4": "Low" },
};

const show = (v: string | null | undefined) => (v == null || v === "" || v === "None" ? "—" : v);

export function CorrectionReasons({ contentType, objectId }: { contentType: number | undefined; objectId: string }) {
    const { data } = useQuery({
        ...recordCorrectionsOptions(contentType ?? 0, objectId),
        enabled: contentType !== undefined && !!objectId,
    });
    const all = data ?? [];
    if (all.length === 0) return null;
    // A lot's hold released by QA is a judgement with its reason on record, not a
    // correction of a wrong value — filed apart, and named by its label, not its code.
    const isRelease = (e: { field_name: string; new_value?: string | null }) =>
        e.field_name === "hold_reason" && !e.new_value;
    // Likewise a work order's priority change (expediting): a decision with its reason,
    // not the correction of a wrong value — and named, not shown as "3 → 1".
    const isDecision = (e: { field_name: string; new_value?: string | null }) =>
        isRelease(e) || e.field_name in DECISION_FIELD_LABELS;
    const groups = [
        { title: "Decisions", edits: all.filter(isDecision) },
        { title: "Corrections", edits: all.filter((e) => !isDecision(e)) },
    ].filter((g) => g.edits.length > 0);
    const valueLabel = (field: string, v: string | null | undefined) =>
        DECISION_FIELD_LABELS[field]?.[v ?? ""] ?? show(v);

    return (
        <div className="space-y-3">
        {groups.map(({ title, edits }) => (
        <div key={title} className="space-y-2 rounded-md border bg-muted/20 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {title} ({edits.length})
            </div>
            <ul className="space-y-2 text-sm">
                {edits.map((e) => (
                    <li key={e.id} className="space-y-0.5">
                        {isRelease(e) ? (
                            <div className="font-medium">
                                Hold released: {HOLD_LABELS[e.old_value ?? ""] ?? show(e.old_value)}
                            </div>
                        ) : (
                        <div className="flex flex-wrap gap-1">
                            <span className="font-medium">{fieldLabel(e.field_name)}:</span>
                            <span className="text-muted-foreground line-through">{valueLabel(e.field_name, e.old_value)}</span>
                            <span className="text-muted-foreground">→</span>
                            <span>{valueLabel(e.field_name, e.new_value)}</span>
                        </div>
                        )}
                        <div className="italic">“{e.reason}”</div>
                        <div className="text-xs text-muted-foreground">
                            {e.edited_by_name || "Unknown"} · {format(new Date(e.edited_at), "PP p")}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
        ))}
        </div>
    );
}
