import { useRetrieveAuditLogEntries } from "@/hooks/useRetrieveAuditLogEntries";
import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { formatDistanceToNow } from "date-fns";

type Props = {
    objectId: string | number;
    modelType: string;
};

const AuditTrailComponent: React.FC<Props> = ({ objectId, modelType }) => {
    const { data: contentTypesRaw } = useRetrieveContentTypes({});

    // Normalize content types (handles both array and paginated formats)
    const contentTypes = Array.isArray(contentTypesRaw) ? contentTypesRaw : contentTypesRaw?.results || [];

    const contentTypeId = contentTypes.find(
        (ct) => ct.model?.toLowerCase() === modelType.toLowerCase()
    )?.id;

    const { data, isLoading, error } = useRetrieveAuditLogEntries({
        queries: {
            object_pk: String(objectId),
            content_type: contentTypeId,
            limit: 5,
            ordering: "-timestamp",
        },
        enabled: !!contentTypeId && !!objectId,
    });

    if (isLoading)
        return <p className="text-sm text-muted-foreground">Loading audit log...</p>;
    if (error)
        return <p className="text-sm text-destructive">Failed to load audit log.</p>;

    const entries = data?.results ?? [];

    if (entries.length === 0) {
        return <p className="text-sm text-muted-foreground">No audit history.</p>;
    }

    return (
        <div className="space-y-6">
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
                                        {entry.actor ?? "System"}
                                    </span>
                                </div>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {formatDistanceToNow(new Date(entry?.timestamp), { addSuffix: true })}
                                </span>
                            </div>
                            
                            <div className="text-sm text-muted-foreground mt-2">
                                {entry.changes && typeof entry.changes === "object"
                                    ? renderChanges(entry.changes, entry.action)
                                    : <span className="italic">No change details available</span>}
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
};

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
    changes: Record<string, unknown>,
    action: number
): React.ReactNode {
    const IGNORED_FIELDS = ["id", "created_at", "modified_at", "created_by"];

    const safeEntries = Object.entries(changes).filter(
        ([field, val]) =>
            !IGNORED_FIELDS.includes(field) &&
            Array.isArray(val) &&
            val.length === 2 &&
            !(val[0] === null && val[1] === null)
    ) as [string, [any, any]][];

    const filtered =
        action === 0
            ? safeEntries.filter(([_, [oldVal]]) => oldVal !== null).slice(0, 3)
            : safeEntries;

    if (filtered.length === 0) {
        return (
            <span className="italic text-muted-foreground">No significant changes</span>
        );
    }

    return (
        <ul className="space-y-0.5 list-disc list-inside">
            {filtered.map(([field, [oldVal, newVal]]) => (
                <li key={field}>
                    <span className="font-medium">{formatFieldName(field)}:</span>{" "}
                    <span className="text-muted-foreground">
            {formatValue(oldVal)} → {formatValue(newVal)}
          </span>
                </li>
            ))}
        </ul>
    );
}

function formatFieldName(field: string): string {
    return field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatValue(val: any): string {
    if (val === null || val === undefined) return "—";
    if (typeof val === "string" && val.startsWith("Tracker.")) {
        const parts = val.split(".");
        return parts[2] ?? parts[1] ?? val;
    }
    return String(val);
}

export default AuditTrailComponent;
