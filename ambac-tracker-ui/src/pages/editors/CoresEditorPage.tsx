import { useCallback, useState } from "react";
import { useRetrieveCores, coresOptions } from "@/hooks/useRetrieveCores";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { format } from "date-fns";
import type { QueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import type { Schema } from "@/lib/api/types";
import { CoresBulkActionsBar, type SelectedCore } from "./CoresBulkActionsBar";

const col = createColumnHelper<Schema<"CoreList">>();
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Play, CheckCircle, Trash2, Eye } from "lucide-react";
import { Link } from "@tanstack/react-router";

// Default params that match what useCoresList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchCoresEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(coresOptions(DEFAULT_LIST_PARAMS));
};

// Custom wrapper hook for consistent usage
function useCoresList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    const queries: Parameters<typeof useRetrieveCores>[0] = { offset, limit, ...filters };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveCores(queries);
}

// Condition grade color mapping
function getConditionBadgeVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}

// Core status color mapping
function getCoreStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status) {
        case 'RECEIVED': return 'secondary';
        case 'IN_DISASSEMBLY': return 'default';
        case 'DISASSEMBLED': return 'outline';
        case 'SCRAPPED': return 'destructive';
        default: return 'outline';
    }
}

type CoreRow = Schema<"CoreList">;

// Actions cell component for cores
function CoreActionsCell({ core }: { core: CoreRow }) {
    const navigate = useNavigate();

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreHorizontal className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                    <Link to="/reman/cores/$id" params={{ id: String(core.id) }}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                    </Link>
                </DropdownMenuItem>
                {core.status === 'RECEIVED' && (
                    <DropdownMenuItem onClick={() => navigate({ to: `/reman/cores/${core.id}/disassembly` })}>
                        <Play className="mr-2 h-4 w-4" />
                        Start Disassembly
                    </DropdownMenuItem>
                )}
                {core.status === 'IN_DISASSEMBLY' && (
                    <DropdownMenuItem onClick={() => navigate({ to: `/reman/cores/${core.id}/disassembly` })}>
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Continue Disassembly
                    </DropdownMenuItem>
                )}
                {core.status === 'RECEIVED' && (
                    <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => navigate({ to: `/reman/cores/${core.id}/scrap` })}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Scrap Core
                    </DropdownMenuItem>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// Adapt a CoreList row to the toolbar's SelectedCore shape.
function toSelectedCore(core: CoreRow): SelectedCore {
    return {
        id: String(core.id),
        core_number: core.core_number ?? String(core.id),
        status: core.status ?? "",
        core_type: (core.core_type ?? null) as string | null,
        core_type_name: core.core_type_name ?? null,
    };
}

export function CoresEditorPage() {
    const navigate = useNavigate();
    // Map keyed by core id so selection survives pagination / filter changes
    // and we keep enough metadata (status, core_type) to drive the toolbar.
    const [selected, setSelected] = useState<Map<string, SelectedCore>>(new Map());
    // Mirror of the rows currently visible on the page (pushed up from
    // ModelEditorPage). Drives the "Select all on page" toolbar action.
    const [pageItems, setPageItems] = useState<SelectedCore[]>([]);

    const handleDataChange = useCallback((items: CoreRow[]) => {
        setPageItems(items.map(toSelectedCore));
    }, []);

    function toggleOne(core: CoreRow) {
        setSelected((prev) => {
            const next = new Map(prev);
            const id = String(core.id);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.set(id, toSelectedCore(core));
            }
            return next;
        });
    }

    function selectAllOnPage() {
        setSelected((prev) => {
            const next = new Map(prev);
            for (const item of pageItems) next.set(item.id, item);
            return next;
        });
    }

    function deselectPage() {
        setSelected((prev) => {
            const next = new Map(prev);
            for (const item of pageItems) next.delete(item.id);
            return next;
        });
    }

    function clearSelection() {
        setSelected(new Map());
    }

    return (
        <>
            <ModelEditorPage
                title="Cores"
                modelName="Cores"
                showDetailsLink={true}
                useList={useCoresList}
                generateDetailLink={(core) => `/reman/cores/${core.id}` as never}
                columns={[
                    col({
                        header: "",
                        priority: 1,
                        renderCell: (core) => {
                            const id = String(core.id);
                            return (
                                <Checkbox
                                    checked={selected.has(id)}
                                    onCheckedChange={() => toggleOne(core)}
                                    onClick={(e) => e.stopPropagation()}
                                    aria-label={`Select ${core.core_number ?? id}`}
                                />
                            );
                        },
                    }),
                    col({
                        header: "Core Number",
                        priority: 1,
                        renderCell: (core) => (
                            <span className="font-mono text-sm font-medium">{core.core_number}</span>
                        ),
                    }),
                    col({
                        header: "Type",
                        priority: 1,
                        renderCell: (core) => core.core_type_name || "—",
                    }),
                    col({
                        header: "Status",
                        priority: 1,
                        renderCell: (core) => {
                            const status = core.status;
                            if (!status) return "—";
                            const labels: Record<string, string> = {
                                'RECEIVED': 'Received',
                                'IN_DISASSEMBLY': 'In Disassembly',
                                'DISASSEMBLED': 'Disassembled',
                                'SCRAPPED': 'Scrapped',
                            };
                            return (
                                <Badge variant={getCoreStatusVariant(status)}>
                                    {labels[status] || status}
                                </Badge>
                            );
                        },
                    }),
                    col({
                        header: "Condition",
                        priority: 2,
                        renderCell: (core) => {
                            const grade = core.condition_grade;
                            if (!grade) return "—";
                            const labels: Record<string, string> = {
                                'A': 'Grade A',
                                'B': 'Grade B',
                                'C': 'Grade C',
                                'SCRAP': 'Scrap',
                            };
                            return (
                                <Badge variant={getConditionBadgeVariant(grade)}>
                                    {labels[grade] || grade}
                                </Badge>
                            );
                        },
                    }),
                    col({
                        header: "Source",
                        priority: 3,
                        renderCell: (core) => {
                            const sourceLabels: Record<string, string> = {
                                'CUSTOMER_RETURN': 'Customer Return',
                                'PURCHASED': 'Purchased',
                                'WARRANTY': 'Warranty',
                                'TRADE_IN': 'Trade-In',
                            };
                            const src = core.source_type;
                            return (src && (sourceLabels[src] ?? src)) || "—";
                        },
                    }),
                    col({
                        header: "Customer",
                        priority: 4,
                        renderCell: (core) => core.customer_name || "—",
                    }),
                    col({
                        header: "Received",
                        priority: 3,
                        renderCell: (core) =>
                            core.received_date
                                ? format(new Date(core.received_date), "MMM d, yyyy")
                                : "—",
                    }),
                    col({
                        header: "Components",
                        priority: 4,
                        renderCell: (core) => {
                            const harvested = core.harvested_component_count ?? 0;
                            const usable = core.usable_component_count ?? 0;
                            if (harvested === 0) return "—";
                            return (
                                <span className="text-sm">
                                    {usable} / {harvested}
                                </span>
                            );
                        },
                    }),
                    col({
                        header: "Credit",
                        priority: 5,
                        renderCell: (core) => {
                            if (!core.core_credit_value) return "—";
                            return (
                                <span className={core.core_credit_issued ? "text-green-600" : ""}>
                                    ${parseFloat(core.core_credit_value).toFixed(2)}
                                    {core.core_credit_issued && " (Issued)"}
                                </span>
                            );
                        },
                    }),
                ]}
                renderActions={(core) => <CoreActionsCell core={core} />}
                onCreate={() => navigate({ to: "/reman/cores/receive" })}
                onDataChange={handleDataChange}
            />
            <CoresBulkActionsBar
                selected={Array.from(selected.values())}
                pageItems={pageItems}
                onSelectAllOnPage={selectAllOnPage}
                onDeselectPage={deselectPage}
                onClear={clearSelection}
            />
        </>
    );
}

export default CoresEditorPage;