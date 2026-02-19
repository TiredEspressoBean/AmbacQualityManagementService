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
import { ExternalLink } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { DataExportMenu } from "@/components/data-export-menu";
import { DataImportDialog } from "@/components/data-import-dialog";

// Link is imported from @tanstack/react-router
import { Link } from "@tanstack/react-router";

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
}

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
    "Equipment-types": "Equipment-types",
    EquipmentTypes: "Equipment-types",

    // QMS
    ErrorReports: "ErrorReports",
    QualityReports: "ErrorReports",
    "Error-types": "Error-types",
    ErrorTypes: "Error-types",
    QuarantineDispositions: "QuarantineDispositions",
    "Sampling-rules": "Sampling-rules",
    SamplingRules: "Sampling-rules",
    "Sampling-rule-sets": "Sampling-rule-sets",
    SamplingRuleSets: "Sampling-rule-sets",
    MeasurementDefinitions: "MeasurementDefinitions",
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
};

/** Column definition with priority-based responsive visibility */
export interface ColumnDef<T> {
    header: string;
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
    /**
     * The model name - used for:
     * 1. Generating detail links (e.g., `/details/Processes/1`)
     * 2. Auto-fetching metadata for search placeholder hints
     * 3. Auto-enabling Excel export
     *
     * Must match a key in MODEL_API_ENDPOINTS (e.g., "Processes", "WorkOrders", "Parts")
     */
    modelName?: string;
    useList: (params: {
        offset: number;
        limit: number;
        ordering?: string;
        search?: string;
        filters?: Record<string, string>;
    }) => {
        data?: { results: T[]; count: number };
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
}

export function ModelEditorPage<T extends { id: string | number }>({
                                                              title,
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
                                                          }: ModelEditorProps<T>) {
    const [offset, setOffset] = useState(0);
    const [limit] = useState(25);
    const [ordering, setOrdering] = useState<string>();
    const [search, setSearch] = useState("");
    const [activeFilters, setActiveFilters] = useState<Record<string, string>>({});
    const debouncedSearch = useDebounce(search, 500);
    const queryClient = useQueryClient();


    // Resolve API endpoint from modelName
    const apiEndpoint = modelName ? MODEL_API_ENDPOINTS[modelName] : undefined;

    const { data, isLoading, error } = useList({
        offset,
        limit,
        ordering,
        search: debouncedSearch,
        filters: activeFilters,
    });

    // Auto-fetch metadata for search field hints based on modelName
    const { data: metadata } = useQuery<ListMetadata>({
        queryKey: ["metadata", modelName, apiEndpoint],
        queryFn: async () => {
            if (!apiEndpoint) return null;
            // Dynamically call the metadata endpoint
            const metadataFn = (api as any)[`api_${apiEndpoint}_metadata_retrieve`];
            if (typeof metadataFn === "function") {
                return metadataFn();
            }
            return null;
        },
        enabled: !!apiEndpoint && !disableMetadata,
        staleTime: Infinity, // Metadata rarely changes
    });

    // Build search placeholder from metadata
    const searchPlaceholder = metadata?.search_fields_display?.length
        ? `Search by ${metadata.search_fields_display.join(", ")}...`
        : `Search ${title.toLowerCase()}...`;

    useEffect(() => {
        setOffset(0);
    }, [debouncedSearch, ordering, activeFilters]);

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
                const { [fieldName]: _, ...rest } = prev;
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

    if (isLoading) return <Skeleton className="h-32 w-full" />;
    if (error) return <p className="text-red-500">Error loading {title}</p>;

    const items = Array.isArray(data?.results) ? data.results : [];
    const total = data?.count || 0;
    const page = Math.floor(offset / limit) + 1;
    const pageCount = Math.ceil(total / limit);

    return (
        <div className="space-y-4">
            {/* Title */}
            <h2 className="text-xl font-semibold">{title}</h2>

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
                        <SelectTrigger className="w-[160px]">
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

                {onCreate && <Button onClick={onCreate}>New {title}</Button>}

                {/* Import/Export - automatically shown if modelName is configured */}
                {apiEndpoint && !disableExport && (
                    <>
                        <DataImportDialog
                            modelName={apiEndpoint}
                            onImportComplete={() => {
                                queryClient.invalidateQueries({ queryKey: [modelName] });
                            }}
                        />
                        <DataExportMenu
                            modelName={apiEndpoint}
                            queryParams={{
                                ordering,
                                search: debouncedSearch,
                                ...activeFilters,
                            }}
                        />
                    </>
                )}

                {/* Optional extra content */}
                {extraToolbarContent && (
                    <div className="ml-auto flex-shrink-0">{extraToolbarContent}</div>
                )}
            </div>

            {/* Table with responsive columns via CSS breakpoints */}
            <Table>
                <TableCaption>{title} List</TableCaption>
                <TableHeader>
                    <TableRow>
                        {columns.map((col, i) => (
                            <TableHead key={i} className={getPriorityClass(col.priority)}>
                                {col.header}
                            </TableHead>
                        ))}
                        {showDetailsLink && <TableHead>Details</TableHead>}
                        {renderActions && <TableHead>Actions</TableHead>}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {items.map((item) => (
                        <TableRow key={item.id}>
                            {columns.map((col, j) => (
                                <TableCell key={j} className={getPriorityClass(col.priority)}>
                                    {col.renderCell(item)}
                                </TableCell>
                            ))}
                            {showDetailsLink && (
                                <TableCell>
                                    <SafeDetailLink item={item} />
                                </TableCell>
                            )}
                            {renderActions && (
                                <TableCell className="text-right space-x-2">
                                    {renderActions(item)}
                                </TableCell>
                            )}
                        </TableRow>
                    ))}
                </TableBody>
            </Table>

            {/* Pagination */}
            <div className="flex justify-between items-center">
                <Button
                    variant="secondary"
                    onClick={() => setOffset(Math.max(offset - limit, 0))}
                    disabled={offset === 0}
                >
                    Previous
                </Button>
                <span>
                    Page {page} of {pageCount}
                </span>
                <Button
                    variant="secondary"
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                >
                    Next
                </Button>
            </div>
        </div>
    );
}