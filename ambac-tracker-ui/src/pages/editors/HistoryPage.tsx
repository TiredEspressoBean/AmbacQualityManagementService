import { useRetrieveAuditLogEntries } from "@/hooks/useRetrieveAuditLogEntries";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { formatDistanceToNow } from "date-fns";

// Matches Django filter fields exactly
function useAuditLogList({
                             offset,
                             limit,
                             ordering,
                             search,
                         }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
}) {
    return useRetrieveAuditLogEntries({
        queries: { offset, limit, ordering, search },
    });
}

export function AuditLogViewerPage() {
    return (
        <ModelEditorPage
            title="Audit Log"
            modelName="AuditLog"
            showDetailsLink={true}
            useList={useAuditLogList}
            sortOptions={[
                { label: "Most Recent", value: "-timestamp" },
                { label: "Oldest First", value: "timestamp" },
                { label: "User (A-Z)", value: "actor" },
                { label: "User (Z-A)", value: "-actor" },
            ]}
            columns={[
                {
                    header: "Time",
                    renderCell: (entry: any) =>
                        formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true }),
                },
                {
                    header: "User",
                    renderCell: (entry: any) => entry.actor ?? "System",
                },
                {
                    header: "Action",
                    renderCell: (entry: any) => actionLabel(entry.action),
                },
                {
                    header: "Object",
                    renderCell: (entry: any) =>
                        entry.content_type_name
                            ? `${entry.content_type_name}: ${entry.object_repr}`
                            : entry.object_repr ?? `#${entry.object_pk}`,
                },
                {
                    header: "Changes",
                    renderCell: (entry: any) =>
                        entry.changes && typeof entry.changes === "object"
                            ? renderChanges(entry.changes, entry.action)
                            : "-",
                },
            ]}
        />
    );
}

function actionLabel(action: number): string {
    switch (action) {
        case 0: return "Create";
        case 1: return "Update";
        case 2: return "Delete";
        default: return "Unknown";
    }
}

function renderChanges(
    changes: Record<string, unknown>,
    action: number
) {
    const IGNORED_FIELDS = [
        "id", "created_at", "modified_at", "created_by",
        "sampled_parts", "supersedes", "rules", "version"
    ];

    const safeEntries = Object.entries(changes).filter(
        ([field, val]) =>
            !IGNORED_FIELDS.includes(field) &&
            Array.isArray(val) &&
            val.length === 2 &&
            !(val[0] === null && val[1] === null)
    ) as [string, [any, any]][];

    const filtered = action === 0
        ? safeEntries.filter(([_, [oldVal]]) => oldVal !== null).slice(0, 3)
        : safeEntries;

    if (filtered.length === 0) {
        return <span className="text-muted-foreground">No significant changes</span>;
    }

    return (
        <div className="space-y-1">
            {filtered.map(([field, [oldVal, newVal]]) => (
                <div key={field}>
                    <strong>{formatFieldName(field)}</strong>: {formatValue(oldVal)} → {formatValue(newVal)}
                </div>
            ))}
        </div>
    );
}

function formatFieldName(field: string): string {
    return field.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

function formatValue(val: any): string {
    if (val === null || val === undefined) return "—";
    if (typeof val === "string" && val.startsWith("Tracker.")) {
        const parts = val.split(".");
        return parts[2] ?? parts[1] ?? val;
    }
    return String(val);
}
