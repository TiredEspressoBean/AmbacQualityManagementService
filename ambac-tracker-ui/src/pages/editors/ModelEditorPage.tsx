import { useState, useEffect, useMemo } from "react";
import {
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/useDebounce";
import { ArchiveRestore, ExternalLink, Plus } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { getCookie } from "@/lib/utils";
import { ALL_TABLES } from "@/lib/data-management/tables";
import { useQuery, queryOptions, useQueryClient } from "@tanstack/react-query";
import { endpointFn } from "@/lib/api/endpoint-fn";
import { DataExportMenu } from "@/components/data-export-menu";
import { DataImportDialog } from "@/components/data-import-dialog";

// Link is imported from @tanstack/react-router
import { Link } from "@tanstack/react-router";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useAuthUser } from "@/hooks/useAuthUser";
import { matchKey } from "@/lib/query-filters";

export type SortOption = { label: string; value: string };

/** Filter choice option */
export interface FilterChoice {
    value: string;
    label: string;
}

/** Filter field metadata */
export interface FilterInfo {
    name: string;
    display: string;
    type: 'text' | 'choice' | 'boolean' | 'foreignkey';
    choices: FilterChoice[] | null;
    related_model?: string;
}

/** Metadata response from /metadata/ endpoint */
export interface ListMetadata {
    search_fields: string[];
    search_fields_display: string[];
    ordering_fields: string[];
    ordering_fields_display: string[];
    filterset_fields: string[];
    filters?: Record<string, FilterInfo>;
    /** Permission codenames for this model, derived server-side from the model so
     *  they can't drift from what the API actually enforces. Null when the viewset
     *  exposes no model. */
    permissions?: {
        add: string; change: string; delete: string; view: string;
    } | null;
}

const modelEditorMetadataOptions = (modelName: string | undefined, apiEndpoint: string | undefined) => queryOptions({
    queryKey: ["metadata", modelName, apiEndpoint] as const,
    queryFn: async () => {
        if (!apiEndpoint) return null;
        // Dynamically call the metadata endpoint.
        // Dynamic alias lookup, and one of the few places `any` is genuinely the
        // right tool. Two alternatives were tried and are worse: a
        // Record<string, unknown> cast needs `as unknown as` (trading this rule
        // for the double-cast one), and `keyof typeof api` makes tsc give up --
        // "Type instantiation is excessively deep" against a 1005-endpoint
        // client. The typeof guard below is what actually makes this safe.
        const metadataFn = endpointFn(apiEndpoint, "metadata_retrieve");
        if (typeof metadataFn === "function") {
            return metadataFn() as Promise<ListMetadata>;
        }
        return null;
    },
});

/**
 * Maps modelName to API endpoint path.
 * Used to automatically derive metadata and export endpoints.
 */
const MODEL_API_ENDPOINTS: Record<string, string> = {
    // MES Lite
    Orders: "Orders",
    Parts: "Parts",
    WorkOrders: "WorkOrders",
    Processes: "Processes",
    PartTypes: "PartTypes",
    Steps: "Steps",
    Equipment: "Equipment",
    Equipments: "Equipment",
    Fixtures: "Fixtures",
    RepairCodes: "RepairCodes",
    "Equipment-types": "Equipment-types",
    EquipmentTypes: "Equipment-types",

    // QMS
    QualityReports: "QualityReports",
    "Error-types": "Error-types",
    ErrorTypes: "Error-types",
    QuarantineDispositions: "QuarantineDispositions",
    "Sampling-rules": "Sampling-rules",
    SamplingRules: "Sampling-rules",
    "Sampling-rule-sets": "Sampling-rule-sets",
    SamplingRuleSets: "Sampling-rule-sets",
    MeasurementDefinitions: "MeasurementDefinitions",
    ReceivingInspectionPlans: "ReceivingInspectionPlans",
    MaterialLots: "MaterialLots",
    Materials: "Materials",
    CAPAs: "CAPAs",
    CapaTasks: "CapaTasks",
    CapaVerifications: "CapaVerifications",
    RcaRecords: "RcaRecords",
    FiveWhys: "FiveWhys",
    Fishbone: "Fishbone",

    // Core
    User: "User",
    Users: "User",
    Companies: "Companies",
    Customers: "Customers",
    Documents: "Documents",
    Groups: "Groups",
    AuditLog: "AuditLog",

    // DMS
    ThreeDModels: "ThreeDModels",
    HeatMapAnnotation: "HeatMapAnnotation",

    // Approvals
    ApprovalTemplates: "ApprovalTemplates",
    ApprovalRequests: "ApprovalRequests",
    ApprovalResponses: "ApprovalResponses",

    // Reman
    Cores: "Cores",
    HarvestedComponents: "HarvestedComponents",
    DisassemblyBOMLines: "DisassemblyBOMLines",

    // Training + calibration (their pages pass the singular model name)
    JobRole: "JobRoles",
    JobRoles: "JobRoles",
    TrainingType: "TrainingTypes",
    TrainingTypes: "TrainingTypes",
    CalibrationRecord: "CalibrationRecords",
    CalibrationRecords: "CalibrationRecords",

    // Scheduling setup
    StepTimings: "StepTimings",
    StepEquipmentAffinities: "StepEquipmentAffinities",
    WorkCenterChangeovers: "WorkCenterChangeovers",

    // Life Tracking
    LifeLimitDefinitions: "LifeLimitDefinitions",
    PartTypeLifeLimits: "PartTypeLifeLimits",
    LifeTracking: "LifeTracking",
};

/**
 * Build a typed column-definition factory bound to a row type.
 *
 * Pair with the strict types from `@/lib/api/types` to get type-checked
 * `renderCell` callbacks — typos like `p.step_descrption` become compile
 * errors.
 *
 * @example
 *   import type { Parts } from "@/lib/api/types";
 *   const col = createColumnHelper<Parts>();
 *   const columns = [
 *     col({ header: "ERP ID", renderCell: (p) => p.ERP_id }),
 *     col({ header: "Step",   renderCell: (p) => p.step_name ?? "—" }),
 *   ];
 *
 * The returned factory just identity-passes the column object; its only
 * job is to capture the row type at the literal site.
 */
export function createColumnHelper<T>() {
    return (col: ColumnDef<T>): ColumnDef<T> => col;
}

/** Column definition with priority-based responsive visibility */
export interface ColumnDef<T> {
    header: string;
    /**
     * Rendered in place of `header` in the column's <th>. For headers that are
     * a control rather than a label — a select-all checkbox, say. `header` is
     * still required, and stays the accessible name.
     */
    headerCell?: React.ReactNode;
    renderCell: (item: T) => React.ReactNode;
    /**
     * Priority for responsive column visibility (lower = more important).
     * - 1: Always visible
     * - 2: Hidden below md (768px)
     * - 3: Hidden below lg (1024px)
     * - 4: Hidden below xl (1280px)
     * - 5+: Hidden below 2xl (1536px)
     * Columns without priority default to always visible.
     */
    priority?: number;
}

/** Maps priority to Tailwind responsive classes */
function getPriorityClass(priority?: number): string {
    if (!priority || priority <= 1) return '';
    switch (priority) {
        case 2: return 'hidden md:table-cell';
        case 3: return 'hidden lg:table-cell';
        case 4: return 'hidden xl:table-cell';
        default: return 'hidden 2xl:table-cell';
    }
}

export interface ModelEditorProps<T> {
    title: string;
    /** Suppress the page-title heading (e.g. when embedded under a tab that
     *  already labels the surface). The title is still used for search
     *  placeholders and the "New {title}" button. */
    hideTitle?: boolean;
    /**
     * The model name - used for:
     * 1. Generating detail links (e.g., `/details/Processes/1`)
     * 2. Auto-fetching metadata for search placeholder hints
     * 3. Auto-enabling Excel export
     *
     * Must match a key in MODEL_API_ENDPOINTS (e.g., "Processes", "WorkOrders", "Parts")
     */
    modelName?: string;
    /**
     * List hook signature is shaped so that any TanStack-Query–based
     * hook (which returns `UseQueryResult<T>` — a discriminated union
     * with `data: T | undefined`) is structurally assignable. With
     * `exactOptionalPropertyTypes: true`, the explicit `data: ... |
     * undefined` matters — `data?:` would NOT accept `data:` from
     * UseQueryResult.
     */
    useList: (params: {
        offset: number;
        limit: number;
        ordering?: string;
        search?: string;
        filters?: Record<string, string>;
    }) => {
        data: { results: T[]; count: number } | undefined;
        isLoading: boolean;
        error: unknown;
    };
    /**
     * Sort options to display. If not provided and modelName is set,
     * options are auto-generated from the metadata endpoint.
     */
    sortOptions?: SortOption[];
    columns: ColumnDef<T>[];
    renderActions?: (item: T) => React.ReactNode;
    onCreate?: () => void;
    /** Optional injected toolbar content, e.g. file upload form */
    extraToolbarContent?: React.ReactNode;
    /** Optional custom link generator, defaults to `/details/${modelName}/${id}` */
    generateDetailLink?: (item: T) => string;
    /** Whether to show the details link column, defaults to true */
    showDetailsLink?: boolean;
    /** Optional header content rendered between title and toolbar (e.g., stats cards) */
    headerContent?: React.ReactNode;
    /** Disable automatic metadata fetching for search hints */
    disableMetadata?: boolean;
    /** Disable the export button */
    disableExport?: boolean;
    /**
     * Query-key prefix of this page's list query, invalidated when an import lands.
     * Defaults to `[modelName]`, which only matches hooks keyed by the model name —
     * pass the hook's real root (e.g. `["job-roles"]`) when it differs.
     */
    listQueryKey?: readonly unknown[];
    /**
     * Notify the parent whenever the current page's items change. Use to
     * drive selection toolbars or other parent-side state that depends on
     * the visible rows without lifting the editor's pagination/filter
     * state. Fires once per query result.
     */
    onDataChange?: (items: T[]) => void;
}

export function ModelEditorPage<T extends { id: string | number }>({
                                                              title,
                                                              hideTitle,
                                                              modelName,
                                                              useList,
                                                              sortOptions,
                                                              columns,
                                                              renderActions,
                                                              onCreate,
                                                              extraToolbarContent,
                                                              generateDetailLink,
                                                              showDetailsLink = true,
                                                              headerContent,
                                                              disableMetadata = false,
                                                              disableExport = false,
                                                              listQueryKey,
                                                              onDataChange,
                                                          }: ModelEditorProps<T>) {
    // Deep-linkable list filters. Any `?key=value` query string on the URL
    // seeds `activeFilters`, so links like `/editor/qualityReports?part=<uuid>`
    // (from the part-detail page's Latest Inspection link) land pre-filtered.
    // Reserved keys the editor owns itself (offset/limit/ordering/search) are
    // excluded so they don't collide with filter names.
    const initialFilters = useMemo(() => {
        if (typeof window === "undefined") return {};
        const params = new URLSearchParams(window.location.search);
        const filters: Record<string, string> = {};
        params.forEach((value, key) => {
            if (["offset", "limit", "ordering", "search", "new"].includes(key)) return;
            filters[key] = value;
        });
        return filters;
    }, []);

    const [offset, setOffset] = useState(0);
    const [limit] = useState(25);
    const [ordering, setOrdering] = useState<string>();
    const [search, setSearch] = useState(() => {
        if (typeof window === "undefined") return "";
        return new URLSearchParams(window.location.search).get("search") ?? "";
    });
    const [activeFilters, setActiveFilters] = useState<Record<string, string>>(initialFilters);
    // Deleting archives a row, so "deleted" rows are still here to find and restore.
    const [showArchived, setShowArchived] = useState(false);
    const debouncedSearch = useDebounce(search, 500);
    const queryClient = useQueryClient();


    // Resolve API endpoint from modelName
    const apiEndpoint = modelName ? MODEL_API_ENDPOINTS[modelName] : undefined;

    // Auto-fetch metadata for search field hints based on modelName (must be before typedFilters)
    const { data: metadata } = useQuery({
        ...modelEditorMetadataOptions(modelName, apiEndpoint),
        enabled: !!apiEndpoint && !disableMetadata,
        staleTime: Infinity, // Metadata rarely changes
    });

    // Hide actions the API would refuse. The server still enforces; this only stops
    // offering a button that can do nothing but 403. Codenames come from metadata
    // (derived from the real model), so no per-page mapping to keep in sync.
    //
    // Two deliberate defaults:
    //  - platform staff bypass, because `effective_permissions` is built from
    //    tenant UserRole groups and is EMPTY for a superuser — gating on it alone
    //    would hide every button from the one account that can always act;
    //  - unknown means allowed. While permissions or metadata are still loading, or
    //    a viewset reports no model, show the button and let the API decide. Failing
    //    closed here would blank the toolbar on every page load.
    const { has: hasPerm, isLoading: permsLoading } = usePermissionSet();
    const { data: authUser } = useAuthUser();
    const isPlatformStaff = (authUser as { is_staff?: boolean } | undefined)?.is_staff ?? false;
    const allows = (codename: string | undefined) => {
        if (!codename || permsLoading || isPlatformStaff) return true;
        return hasPerm(codename);
    };
    const canCreate = allows(metadata?.permissions?.add);

    // Convert filter values to proper types based on metadata
    const typedFilters = useMemo(() => {
        if (!metadata?.filters) return activeFilters;
        const result: Record<string, string | boolean> = {};
        for (const [key, value] of Object.entries(activeFilters)) {
            const filterMeta = metadata.filters[key];
            if (filterMeta?.type === 'boolean') {
                result[key] = value === 'true';
            } else {
                result[key] = value;
            }
        }
        return result;
    }, [activeFilters, metadata]);

    const listFilters = useMemo(
        () => (showArchived ? { ...typedFilters, include_archived: "true" } : typedFilters) as Record<string, string>,
        [typedFilters, showArchived],
    );
    const { data, isLoading, error } = useList({
        offset,
        limit,
        ordering,
        search: debouncedSearch,
        filters: listFilters,
    });

    // Build search placeholder from metadata
    const searchPlaceholder = metadata?.search_fields_display?.length
        ? `Search by ${metadata.search_fields_display.join(", ")}...`
        : `Search ${title.toLowerCase()}...`;

    useEffect(() => {
        setOffset(0);
    }, [debouncedSearch, ordering, activeFilters, showArchived]);

    // A table listed in Data Management links back to it.
    const inDataManagement = !!apiEndpoint && ALL_TABLES.some((t) => t.endpoint === apiEndpoint);
    const canRestore = allows(metadata?.permissions?.change);
    const [restoring, setRestoring] = useState<string | number | null>(null);
    const restore = async (item: T) => {
        const patch = apiEndpoint ? endpointFn(apiEndpoint, "partial_update") : undefined;
        if (typeof patch !== "function") return;
        setRestoring(item.id);
        try {
            // An archived row is hidden from the detail route too unless asked for.
            await patch({ archived: false }, {
                params: { id: String(item.id) },
                queries: { include_archived: "true" },
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            });
            toast.success("Restored");
            // Pages key their lists their own way (not always [modelName]); what's on
            // screen is the list, so refetch that.
            queryClient.invalidateQueries({ type: "active" });
        } catch {
            toast.error("Couldn't restore it — another row may now hold its name or key.");
        } finally {
            setRestoring(null);
        }
    };
    const isArchived = (item: T) => (item as { archived?: boolean }).archived === true;

    // Bulk archive, the Django admin's "delete selected". Only on Data Management
    // tables, and not where a page draws its own selection column (a header cell
    // that is a control) — Cores has its own bulk bar.
    const destroyFn = apiEndpoint ? endpointFn(apiEndpoint, "destroy") : undefined;
    const bulkEnabled = inDataManagement && typeof destroyFn === "function"
        && allows(metadata?.permissions?.delete) && !columns.some((c) => c.headerCell);
    const [selected, setSelected] = useState<Set<string | number>>(new Set());
    const [archiving, setArchiving] = useState(false);
    useEffect(() => { setSelected(new Set()); }, [offset, debouncedSearch, ordering, activeFilters, showArchived]);
    const archiveSelected = async () => {
        if (typeof destroyFn !== "function" || selected.size === 0) return;
        if (!window.confirm(`Archive ${selected.size} ${selected.size === 1 ? "row" : "rows"}? They can be restored with "Show archived".`)) return;
        setArchiving(true);
        const headers = { "X-CSRFToken": getCookie("csrftoken") };
        const results = await Promise.allSettled([...selected].map((id) =>
            destroyFn(undefined, { params: { id: String(id) }, headers })));
        const failed = results.filter((r) => r.status === "rejected").length;
        setArchiving(false);
        setSelected(new Set());
        queryClient.invalidateQueries({ type: "active" });
        if (failed) toast.error(`${failed} couldn't be archived — something still depends on them.`);
        else toast.success(`Archived ${results.length}`);
    };

    // Notify parent (used by selection-toolbar consumers like CoresEditorPage
    // to mirror the current page's rows without lifting list state).
    useEffect(() => {
        if (onDataChange && data?.results) {
            onDataChange(data.results);
        }
    }, [data?.results, onDataChange]);

    // Get filterable fields from metadata (choice and boolean types only for now)
    const filterableFields = useMemo(() => {
        if (!metadata?.filters) return [];
        return Object.values(metadata.filters).filter(
            (f) => (f.type === 'choice' || f.type === 'boolean') && f.choices
        );
    }, [metadata]);

    // Auto-generate sort options from metadata if not provided
    const effectiveSortOptions = useMemo<SortOption[]>(() => {
        // Use provided sortOptions if available
        if (sortOptions && sortOptions.length > 0) {
            return sortOptions;
        }
        // Generate from metadata
        if (!metadata?.ordering_fields || !metadata?.ordering_fields_display) {
            return [];
        }
        const options: SortOption[] = [];
        metadata.ordering_fields.forEach((field, index) => {
            const display = metadata.ordering_fields_display[index] || field;
            // Detect field type for better labels
            const isDateField = field.includes('created') || field.includes('updated') ||
                               field.includes('date') || field.includes('_at') || field.includes('completion');
            const isNumericField = field.includes('count') || field.includes('quantity') ||
                                  field.includes('number') || field.includes('priority') || field.includes('order');

            if (isDateField) {
                options.push(
                    { label: `${display} (Newest)`, value: `-${field}` },
                    { label: `${display} (Oldest)`, value: field }
                );
            } else if (isNumericField) {
                options.push(
                    { label: `${display} (High-Low)`, value: `-${field}` },
                    { label: `${display} (Low-High)`, value: field }
                );
            } else {
                options.push(
                    { label: `${display} (A-Z)`, value: field },
                    { label: `${display} (Z-A)`, value: `-${field}` }
                );
            }
        });
        return options;
    }, [sortOptions, metadata]);

    // Handler for filter changes
    const handleFilterChange = (fieldName: string, value: string) => {
        setActiveFilters((prev) => {
            if (!value || value === '__all__') {
                // Remove filter if cleared
                const { [fieldName]: _dropped, ...rest } = prev;
                void _dropped;
                return rest;
            }
            return { ...prev, [fieldName]: value };
        });
    };

    // Default link generator with validation
    const defaultGenerateDetailLink = (item: T) => {
        if (!modelName) {
            console.warn('ModelEditorPage: modelName is required when showDetailsLink is true');
            return `/details/unknown/${item.id}`;
        }
        return `/details/${modelName}/${item.id}`;
    };
    const linkGenerator = generateDetailLink || defaultGenerateDetailLink;

    // Safe link component that handles missing router and validates modelName
    const SafeDetailLink = ({ item }: { item: T }) => {
        const linkTo = linkGenerator(item);

        // Don't render link if modelName is missing and no custom generator provided
        if (!modelName && !generateDetailLink) {
            return (
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2"
                    disabled
                    title="Details link not configured"
                >
                    <span className="flex items-center gap-1 opacity-50">
                        <ExternalLink className="h-3 w-3" />
                        View
                    </span>
                </Button>
            );
        }

        if (Link) {
            // React Router is available
            return (
                <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="h-8 px-2"
                >
                    <Link
                        to={linkTo}
                        className="flex items-center gap-1"
                    >
                        <ExternalLink className="h-3 w-3" />
                        View
                    </Link>
                </Button>
            );
        } else {
            // Fallback to regular navigation
            return (
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 px-2"
                    onClick={() => {
                        window.location.href = linkTo;
                    }}
                >
                    <span className="flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" />
                        View
                    </span>
                </Button>
            );
        }
    };

    if (isLoading) return (
        <div className="space-y-4 p-6">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-72 w-full rounded-md" />
        </div>
    );
    if (error) return (
        <div className="p-6">
            <p className="text-sm text-destructive">Couldn't load {title.toLowerCase()}. Try refreshing.</p>
        </div>
    );

    const items = Array.isArray(data?.results) ? data.results : [];
    // Only rows that carry `archived` can be shown archived and restored; a model
    // with its own lifecycle (deactivated users, deprecated processes) doesn't.
    // Unknown until a row loads, so an empty table keeps the switch.
    const tracksArchived = items.length === 0 || items.some((i) => "archived" in (i as object));
    const total = data?.count || 0;
    const page = Math.floor(offset / limit) + 1;
    const pageCount = Math.ceil(total / limit);

    return (
        // Page-owned gutters — Layout's <main> has no padding so each page
        // is responsible for its own breathing room from the sidebar/chrome.
        <div className="space-y-4 p-6 pb-24">
            {/* Title */}
            {inDataManagement && !hideTitle && (
                <Link to="/Edit" className="text-sm text-muted-foreground hover:text-foreground hover:underline">
                    Data Management
                </Link>
            )}
            {!hideTitle && (
                <div className="flex items-baseline gap-3">
                    <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
                    <span className="text-sm text-muted-foreground tabular-nums">{total} total</span>
                </div>
            )}

            {/* Optional header content (e.g., stats cards) */}
            {headerContent}

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-4">
                <Input
                    placeholder={searchPlaceholder}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="flex-1 min-w-[200px]"
                />
                {effectiveSortOptions.length > 0 && (
                    <Select onValueChange={setOrdering} value={ordering}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Sort by..." />
                        </SelectTrigger>
                        <SelectContent>
                            {effectiveSortOptions.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                )}

                {/* Auto-generated filter dropdowns from metadata */}
                {filterableFields.map((filter) => (
                    <Select
                        key={filter.name}
                        onValueChange={(val) => handleFilterChange(filter.name, val)}
                        value={activeFilters[filter.name] || '__all__'}
                    >
                        <SelectTrigger className="w-[160px] xl:hidden">
                            <SelectValue placeholder={filter.display} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="__all__">All {filter.display}</SelectItem>
                            {filter.choices?.map((choice) => (
                                <SelectItem key={choice.value} value={choice.value}>
                                    {choice.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                ))}

                {apiEndpoint && tracksArchived && (
                    <div className="flex items-center gap-2">
                        <Switch id={`show-archived-${apiEndpoint}`} checked={showArchived} onCheckedChange={setShowArchived} />
                        <Label htmlFor={`show-archived-${apiEndpoint}`} className="text-sm font-normal">Show archived</Label>
                    </div>
                )}

                {/* Right-aligned action group: create + import/export + any extra. */}
                <div className="ml-auto flex flex-shrink-0 items-center gap-2">
                    {apiEndpoint && !disableExport && (
                        <>
                            {/* Only what the backend has: an Import button on a model
                                with no import endpoint opened a dialog whose every
                                call 404'd. */}
                            {typeof endpointFn(apiEndpoint, "import_create") === "function" && (
                                <DataImportDialog
                                    modelName={apiEndpoint}
                                    onImportComplete={() => {
                                        queryClient.invalidateQueries(matchKey(listQueryKey ?? [modelName]));
                                    }}
                                />
                            )}
                            {typeof endpointFn(apiEndpoint, "export_retrieve") === "function" && (
                                <DataExportMenu
                                    modelName={apiEndpoint}
                                    showTemplateOption={typeof endpointFn(apiEndpoint, "import_template_retrieve") === "function"}
                                    queryParams={{
                                        ordering,
                                        search: debouncedSearch,
                                        ...activeFilters,
                                        ...(showArchived ? { include_archived: "true" } : {}),
                                    }}
                                />
                            )}
                        </>
                    )}
                    {extraToolbarContent}
                    {onCreate && canCreate && (
                        <Button onClick={onCreate}>
                            <Plus className="mr-1 h-4 w-4" /> New {title}
                        </Button>
                    )}
                </div>
            </div>

            {selected.size > 0 && (
                <div className="flex items-center gap-3 rounded-md border bg-muted/50 px-3 py-2 text-sm">
                    <span className="tabular-nums">{selected.size} selected</span>
                    <Button size="sm" variant="outline" disabled={archiving} onClick={() => void archiveSelected()}>
                        {archiving ? "Archiving…" : "Archive selected"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
                </div>
            )}

            {/* Table with responsive columns via CSS breakpoints. The wrapper
                makes the table horizontally scrollable on narrow screens and
                the rightmost action column (Actions if present, else Details)
                is sticky-right so it stays visible while scrolling. */}
            <div className="flex items-start gap-6">
            <div className="min-w-0 flex-1 space-y-4">
            <div className="relative w-full overflow-x-auto rounded-md border">
                <Table>
                    <TableCaption className="sr-only">{title} list</TableCaption>
                    <TableHeader>
                        <TableRow>
                            {bulkEnabled && (
                                <TableHead className="w-10">
                                    <Checkbox
                                        aria-label="Select every row on this page"
                                        checked={items.length > 0 && items.filter((i) => !isArchived(i)).every((i) => selected.has(i.id))}
                                        onCheckedChange={(v) => setSelected(v === true
                                            ? new Set(items.filter((i) => !isArchived(i)).map((i) => i.id))
                                            : new Set())}
                                    />
                                </TableHead>
                            )}
                            {columns.map((col, i) => (
                                <TableHead key={i} className={getPriorityClass(col.priority)}>
                                    {col.headerCell ?? col.header}
                                </TableHead>
                            ))}
                            {showDetailsLink && (
                                <TableHead
                                    className={
                                        // Sticky-right only when there's no Actions column
                                        // to its right — otherwise the Actions column wins.
                                        renderActions
                                            ? undefined
                                            : "sticky right-0 z-10 bg-background shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.1)]"
                                    }
                                >
                                    Details
                                </TableHead>
                            )}
                            {renderActions && (
                                <TableHead className="sticky right-0 z-10 bg-background text-right shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.1)]">
                                    Actions
                                </TableHead>
                            )}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {items.map((item) => (
                            <TableRow key={item.id} className={isArchived(item) ? "text-muted-foreground" : undefined}
                                data-state={selected.has(item.id) ? "selected" : undefined}>
                                {bulkEnabled && (
                                    <TableCell className="w-10">
                                        {!isArchived(item) && (
                                            <Checkbox
                                                aria-label="Select row"
                                                checked={selected.has(item.id)}
                                                onCheckedChange={(v) => setSelected((prev) => {
                                                    const next = new Set(prev);
                                                    if (v === true) next.add(item.id); else next.delete(item.id);
                                                    return next;
                                                })}
                                            />
                                        )}
                                    </TableCell>
                                )}
                                {columns.map((col, j) => (
                                    <TableCell key={j} className={getPriorityClass(col.priority)}>
                                        {j === 0 && isArchived(item) && (
                                            <Badge variant="outline" className="mr-2">Archived</Badge>
                                        )}
                                        {col.renderCell(item)}
                                    </TableCell>
                                ))}
                                {showDetailsLink && (
                                    <TableCell
                                        className={
                                            renderActions
                                                ? undefined
                                                : "sticky right-0 z-10 bg-background shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.1)]"
                                        }
                                    >
                                        <SafeDetailLink item={item} />
                                    </TableCell>
                                )}
                                {renderActions && (
                                    <TableCell className="sticky right-0 z-10 bg-background text-right space-x-2 shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.1)]">
                                        {isArchived(item) ? (
                                            canRestore && (
                                                <Button variant="ghost" size="sm" disabled={restoring === item.id}
                                                    onClick={() => void restore(item)}>
                                                    <ArchiveRestore className="mr-1 h-4 w-4" /> Restore
                                                </Button>
                                            )
                                        ) : renderActions(item)}
                                    </TableCell>
                                )}
                            </TableRow>
                        ))}
                        {items.length === 0 && (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length + (bulkEnabled ? 1 : 0) + (showDetailsLink ? 1 : 0) + (renderActions ? 1 : 0)}
                                    className="h-24 text-center text-muted-foreground"
                                >
                                    No {title.toLowerCase()} found
                                    {debouncedSearch ? ` for "${debouncedSearch}"` : ""}.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            {total > 0 && (
                <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground tabular-nums">
                        {total} result{total === 1 ? "" : "s"}
                    </span>
                    <div className="flex items-center gap-3">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setOffset(Math.max(offset - limit, 0))}
                            disabled={offset === 0}
                        >
                            Previous
                        </Button>
                        <span className="text-muted-foreground tabular-nums">
                            Page {page} of {pageCount || 1}
                        </span>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setOffset(offset + limit)}
                            disabled={offset + limit >= total}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            )}
            </div>

            {/* Filter panel beside the table on wide screens, the way the Django admin
                lists its filters; narrower screens keep the toolbar dropdowns. */}
            {filterableFields.length > 0 && (
                <aside className="hidden w-56 shrink-0 overflow-hidden rounded-md border xl:block" aria-label="Filters">
                    <div className="flex h-9 items-center justify-between border-b bg-muted/60 px-3">
                        <h2 className="text-xs font-semibold uppercase tracking-wider">Filter</h2>
                        {Object.keys(activeFilters).length > 0 && (
                            <button type="button" className="text-xs text-muted-foreground hover:underline"
                                onClick={() => setActiveFilters({})}>Clear</button>
                        )}
                    </div>
                    <div className="space-y-4 p-3">
                        {filterableFields.map((filter) => {
                            const current = activeFilters[filter.name];
                            const options = [{ value: "__all__", label: "All" }, ...(filter.choices ?? [])];
                            return (
                                <div key={filter.name} className="space-y-1">
                                    <h3 className="text-xs font-semibold text-muted-foreground">By {filter.display.toLowerCase()}</h3>
                                    <ul className="space-y-0.5">
                                        {options.map((o) => {
                                            const on = (current ?? "__all__") === o.value;
                                            return (
                                                <li key={o.value}>
                                                    <button type="button" aria-pressed={on}
                                                        onClick={() => handleFilterChange(filter.name, o.value)}
                                                        className={`w-full rounded px-1.5 py-0.5 text-left text-sm hover:bg-muted ${on ? "font-semibold" : "text-muted-foreground"}`}>
                                                        {o.label}
                                                    </button>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            );
                        })}
                    </div>
                </aside>
            )}
            </div>
        </div>
    );
}