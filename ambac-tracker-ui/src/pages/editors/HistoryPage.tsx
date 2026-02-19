import { useRetrieveAuditLogEntries } from "@/hooks/useRetrieveAuditLogEntries";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { formatDistanceToNow, format } from "date-fns";
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Eye } from "lucide-react";

// Default params for prefetching
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    ordering: "-timestamp",
    search: "",
};

// Prefetch function for route loader
export const prefetchAuditLogEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["logs", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_auditlog_list(DEFAULT_LIST_PARAMS),
    });
};

// Custom wrapper hook that properly passes filters
function useAuditLogList({
    offset,
    limit,
    ordering,
    search,
    filters,
}: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    return useRetrieveAuditLogEntries({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

// Map content_type_name to route model names
const CONTENT_TYPE_TO_MODEL: Record<string, string> = {
    order: "Orders",
    orders: "Orders",
    part: "Parts",
    parts: "Parts",
    workorder: "WorkOrders",
    work_order: "WorkOrders",
    process: "Processes",
    processes: "Processes",
    step: "Steps",
    steps: "Steps",
    parttype: "PartTypes",
    part_type: "PartTypes",
    equipment: "Equipment",
    equipmenttype: "EquipmentTypes",
    equipment_type: "EquipmentTypes",
    errortype: "ErrorTypes",
    error_type: "ErrorTypes",
    documents: "Documents",
    document: "Documents",
    company: "Companies",
    companies: "Companies",
    user: "User",
    capa: "CAPAs",
    qualityreport: "QualityReports",
    quality_report: "QualityReports",
    errorreport: "QualityReports",
    error_report: "QualityReports",
    threedmodel: "ThreeDModels",
    three_d_model: "ThreeDModels",
    samplingrule: "SamplingRules",
    sampling_rule: "SamplingRules",
    samplingruleset: "SamplingRuleSets",
    sampling_rule_set: "SamplingRuleSets",
    approvaltemplate: "ApprovalTemplates",
    approval_template: "ApprovalTemplates",
};

// Generate link to the object if possible
function getObjectLink(entry: any): string | null {
    if (!entry.content_type_name || !entry.object_pk) return null;

    const normalized = entry.content_type_name.toLowerCase().replace(/\s+/g, "");
    const modelName = CONTENT_TYPE_TO_MODEL[normalized];

    if (!modelName) return null;

    return `/details/${modelName}/${entry.object_pk}`;
}

// Action badge component for audit log actions
function ActionBadge({ action }: { action: number }) {
    const config = {
        0: { label: "Created", icon: Plus, className: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800" },
        1: { label: "Updated", icon: Pencil, className: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800" },
        2: { label: "Deleted", icon: Trash2, className: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800" },
        3: { label: "Accessed", icon: Eye, className: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700" },
    }[action] ?? { label: "Unknown", icon: Eye, className: "bg-gray-100 text-gray-800 border-gray-200" };

    const Icon = config.icon;

    return (
        <Badge
            variant="outline"
            className={cn("inline-flex items-center gap-1 text-xs px-2 py-1 font-medium", config.className)}
        >
            <Icon className="h-3 w-3" />
            {config.label}
        </Badge>
    );
}

// Render the object cell with optional link
function ObjectCell({ entry }: { entry: any }) {
    const link = getObjectLink(entry);
    const display = entry.content_type_name
        ? `${entry.content_type_name}: ${entry.object_repr}`
        : entry.object_repr ?? `#${entry.object_pk}`;

    if (link && entry.action !== 2) {
        // Don't link deleted objects
        return (
            <Link
                to={link}
                className="text-primary hover:underline font-medium"
            >
                {display}
            </Link>
        );
    }

    return <span className={entry.action === 2 ? "text-muted-foreground line-through" : ""}>{display}</span>;
}

export function AuditLogViewerPage() {
    return (
        <ModelEditorPage
            title="Audit Log"
            modelName="AuditLog"
            showDetailsLink={true}
            disableExport={true}
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
                    priority: 1,
                    renderCell: (entry: any) => (
                        <div className="flex flex-col">
                            <span className="text-sm">
                                {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                            </span>
                            <span className="text-xs text-muted-foreground">
                                {format(new Date(entry.timestamp), "MMM d, h:mm a")}
                            </span>
                        </div>
                    ),
                },
                {
                    header: "User",
                    priority: 1,
                    renderCell: (entry: any) => (
                        <span className="font-medium">
                            {entry.actor_info?.username || entry.actor || "System"}
                        </span>
                    ),
                },
                {
                    header: "Action",
                    priority: 1,
                    renderCell: (entry: any) => <ActionBadge action={entry.action} />,
                },
                {
                    header: "Object",
                    priority: 2,
                    renderCell: (entry: any) => <ObjectCell entry={entry} />,
                },
                {
                    header: "Changes",
                    priority: 3,
                    renderCell: (entry: any) =>
                        entry.changes && typeof entry.changes === "object"
                            ? renderChanges(entry.changes, entry.action)
                            : <span className="text-muted-foreground">—</span>,
                },
            ]}
        />
    );
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
        return <span className="text-muted-foreground text-sm">No significant changes</span>;
    }

    return (
        <div className="space-y-1 text-sm">
            {filtered.slice(0, 4).map(([field, [oldVal, newVal]]) => (
                <div key={field} className="flex flex-wrap gap-1">
                    <span className="font-medium">{formatFieldName(field)}:</span>
                    <span className="text-red-600 dark:text-red-400 line-through">{formatValue(oldVal)}</span>
                    <span className="text-muted-foreground">→</span>
                    <span className="text-green-600 dark:text-green-400">{formatValue(newVal)}</span>
                </div>
            ))}
            {filtered.length > 4 && (
                <span className="text-muted-foreground text-xs">
                    +{filtered.length - 4} more changes
                </span>
            )}
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
    if (typeof val === "string" && val.length > 30) {
        return val.substring(0, 30) + "...";
    }
    return String(val);
}
