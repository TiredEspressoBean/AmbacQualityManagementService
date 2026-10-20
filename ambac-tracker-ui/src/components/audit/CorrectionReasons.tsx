/**
 * Corrections made to one record, each with the reason given for it (RecordEdit):
 * field · old → new · reason, who and when. Shown inside a record's History so the
 * "why" sits beside the "what". Renders nothing when the record has no corrections.
 */
import { queryOptions, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";

import { api } from "@/lib/api/generated";

export const recordCorrectionsOptions = (contentType: number, objectId: string) =>
    queryOptions({
        queryKey: ["record-edits", contentType, objectId] as const,
        queryFn: () => api.api_RecordEdits_list({ queries: { content_type: contentType, object_id: objectId } }),
    });

const fieldLabel = (f: string) => f.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const show = (v: string | null | undefined) => (v == null || v === "" || v === "None" ? "—" : v);

export function CorrectionReasons({ contentType, objectId }: { contentType: number | undefined; objectId: string }) {
    const { data } = useQuery({
        ...recordCorrectionsOptions(contentType ?? 0, objectId),
        enabled: contentType !== undefined && !!objectId,
    });
    const edits = data ?? [];
    if (edits.length === 0) return null;

    return (
        <div className="space-y-2 rounded-md border bg-muted/20 p-3">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Corrections ({edits.length})
            </div>
            <ul className="space-y-2 text-sm">
                {edits.map((e) => (
                    <li key={e.id} className="space-y-0.5">
                        <div className="flex flex-wrap gap-1">
                            <span className="font-medium">{fieldLabel(e.field_name)}:</span>
                            <span className="text-muted-foreground line-through">{show(e.old_value)}</span>
                            <span className="text-muted-foreground">→</span>
                            <span>{show(e.new_value)}</span>
                        </div>
                        <div className="italic">“{e.reason}”</div>
                        <div className="text-xs text-muted-foreground">
                            {e.edited_by_name || "Unknown"} · {format(new Date(e.edited_at), "PP p")}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
