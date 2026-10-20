import { useEffect } from "react";
import { useRetrieveAuditLogEntries } from "@/hooks/useRetrieveAuditLogEntries";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { format, formatDistanceToNow } from "date-fns";
import { CorrectionReasons } from "@/components/audit/CorrectionReasons";

type Props = {
    objectId: string | number;
    modelType: string;
};

const AuditTrailComponent: React.FC<Props> = ({ objectId, modelType }) => {
    const { data: contentTypesRaw } = useRetrieveContentTypes({});

    // Normalize content types (handles both array and paginated formats)
    const contentTypes = Array.isArray(contentTypesRaw) ? contentTypesRaw : [];

    const contentTypeId = resolveContentTypeId(contentTypes, modelType);
    const typesLoaded = contentTypes.length > 0;
    const unresolved = typesLoaded && contentTypeId === undefined;
    useEffect(() => {
        // Loud in development: an unplaceable model is a config gap, not a quiet record.
        if (unresolved && import.meta.env.DEV) {
            console.warn(`AuditTrail: no content type for modelType "${modelType}" — add it to CONTENT_TYPE_ALIASES.`);
        }
    }, [unresolved, modelType]);

    const { data, isLoading, error } = useRetrieveAuditLogEntries({
        object_pk: String(objectId),
        content_type: contentTypeId,
        limit: 5,
        ordering: "-timestamp",
    }, undefined, {
        enabled: !!contentTypeId && !!objectId,
    });

    // A model the lookup can't place must say so — it used to fall through to "No
    // audit history", indistinguishable from a record that genuinely has none.
    if (unresolved)
        return <p className="text-sm text-muted-foreground">Activity history isn&rsquo;t available for this kind of record.</p>;
    if (isLoading)
        return <p className="text-sm text-muted-foreground">Loading audit log...</p>;
    if (error)
        return <p className="text-sm text-destructive">Failed to load audit log.</p>;

    const entries = data?.results ?? [];
    const corrections = <CorrectionReasons contentType={contentTypeId} objectId={String(objectId)} />;

    if (entries.length === 0) {
        return (
            <div className="space-y-4">
                {corrections}
                <p className="text-sm text-muted-foreground">No audit history.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {corrections}
            {entries.map((entry, index) => (
                <div key={entry.id} className="relative">
                    {/* Timeline indicator */}
                    <div className="flex items-start gap-4">
                        <div className="flex flex-col items-center">
                            <div className={`w-3 h-3 rounded-full border-2 ${
                                entry.action === 0 ? 'bg-green-100 border-green-500' :
                                entry.action === 1 ? 'bg-blue-100 border-blue-500' :
                                'bg-red-100 border-red-500'
                            }`} />
                            {index < entries.length - 1 && (
                                <div className="w-px h-8 bg-border mt-2" />
                            )}
                        </div>
                        
                        {/* Content */}
                        <div className="flex-1 min-w-0 pb-4">
                            <div className="flex items-start justify-between gap-2 mb-1">
                                <div className="flex items-center gap-2">
                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                        entry.action === 0 ? 'bg-green-100 text-green-800' :
                                        entry.action === 1 ? 'bg-blue-100 text-blue-800' :
                                        'bg-red-100 text-red-800'
                                    }`}>
                                        {actionLabel(entry.action)}
                                    </span>
                                    <span className="text-sm font-medium text-foreground">
                                        {actorName(entry.actor_info) ?? (entry.actor != null ? `User ${entry.actor}` : "System")}
                                    </span>
                                </div>
                                {/* The absolute time is the record; the relative one is a convenience. */}
                                <span className="text-right text-xs text-muted-foreground whitespace-nowrap tabular-nums">
                                    {format(new Date(entry.timestamp), "PP p")}
                                    <span className="block">{formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}</span>
                                </span>
                            </div>
                            
                            <div className="text-sm text-muted-foreground mt-2">
                                {/* changes_display names foreign keys ("Released By: Jennifer Walsh",
                                    not 187) and drops empty values; built server-side. */}
                                {renderChanges(entry.changes_display ?? [], entry.action)}
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

/** Detail-page model names that aren't their Django model's name. */
const CONTENT_TYPE_ALIASES: Record<string, string> = {
    customers: "user",          // the Customers view lists User rows
    users: "user",
    errortypes: "qualityerrorslist",
    trackerorders: "orders",
};

/**
 * The content type for a detail page's modelType. Content types are the lowercased
 * class name (`workorder`), while page configs are often plural (`workorders`), so an
 * exact match silently missed nine pages. Tries the alias, the name as given, then
 * the name without its plural "s".
 */
function resolveContentTypeId(types: { model?: string; id?: number }[], modelType: string): number | undefined {
    const want = modelType.toLowerCase();
    const candidates = [CONTENT_TYPE_ALIASES[want], want, want.endsWith("s") ? want.slice(0, -1) : undefined]
        .filter((c): c is string => !!c);
    for (const c of candidates) {
        const hit = types.find((t) => t.model?.toLowerCase() === c);
        if (hit?.id !== undefined) return hit.id;
    }
    return undefined;
}

/** A person's name, not their numeric id: "Maria Santos", else the username. */
function actorName(info: { first_name?: string | null; last_name?: string | null; username?: string } | null | undefined): string | null {
    if (!info) return null;
    const full = [info.first_name, info.last_name].filter(Boolean).join(" ").trim();
    return full || info.username || null;
}

function actionLabel(action: number): string {
    switch (action) {
        case 0:
            return "Created";
        case 1:
            return "Updated";
        case 2:
            return "Deleted";
        default:
            return "Unknown";
    }
}

function renderChanges(
    changes: { field: string; old?: string | null; new?: string | null }[],
    action: number
): React.ReactNode {
    // A create lists only the first few fields set; an update lists every change.
    const shown = action === 0 ? changes.slice(0, 3) : changes;
    if (shown.length === 0) {
        return <span className="italic text-muted-foreground">No significant changes</span>;
    }
    return (
        <ul className="space-y-0.5 list-disc list-inside">
            {shown.map((c) => (
                <li key={c.field}>
                    <span className="font-medium">{formatFieldName(c.field)}:</span>{" "}
                    <span className="text-muted-foreground">
                        {action === 0 || c.old == null ? (c.new ?? "—") : `${c.old} → ${c.new ?? "—"}`}
                    </span>
                </li>
            ))}
        </ul>
    );
}

function formatFieldName(field: string): string {
    return field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}


export default AuditTrailComponent;
