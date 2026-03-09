import { useRetrieveCores } from "@/hooks/useRetrieveCores";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
    queryClient.prefetchQuery({
        queryKey: ["cores", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Cores_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Cores", "Cores"],
        queryFn: () => api.api_Cores_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function useCoresList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    return useRetrieveCores({
        offset, limit, ordering, search, ...filters,
    });
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

// Actions cell component for cores
function CoreActionsCell({ core }: { core: any }) {
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
                    <Link to={`/reman/cores/${core.id}`}>
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

export function CoresEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Cores"
            modelName="Cores"
            showDetailsLink={true}
            useList={useCoresList}
            generateDetailLink={(core: any) => `/reman/cores/${core.id}`}
            columns={[
                {
                    header: "Core Number",
                    priority: 1,
                    renderCell: (core: any) => (
                        <span className="font-mono text-sm font-medium">{core.core_number}</span>
                    ),
                },
                {
                    header: "Type",
                    priority: 1,
                    renderCell: (core: any) => core.core_type_name || "—",
                },
                {
                    header: "Status",
                    priority: 1,
                    renderCell: (core: any) => {
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
                },
                {
                    header: "Condition",
                    priority: 2,
                    renderCell: (core: any) => {
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
                },
                {
                    header: "Source",
                    priority: 3,
                    renderCell: (core: any) => {
                        const sourceLabels: Record<string, string> = {
                            'CUSTOMER_RETURN': 'Customer Return',
                            'PURCHASED': 'Purchased',
                            'WARRANTY': 'Warranty',
                            'TRADE_IN': 'Trade-In',
                        };
                        return sourceLabels[core.source_type] || core.source_type || "—";
                    },
                },
                {
                    header: "Customer",
                    priority: 4,
                    renderCell: (core: any) => core.customer_name || "—",
                },
                {
                    header: "Received",
                    priority: 3,
                    renderCell: (core: any) =>
                        core.received_date
                            ? format(new Date(core.received_date), "MMM d, yyyy")
                            : "—",
                },
                {
                    header: "Components",
                    priority: 4,
                    renderCell: (core: any) => {
                        const harvested = core.harvested_component_count ?? 0;
                        const usable = core.usable_component_count ?? 0;
                        if (harvested === 0) return "—";
                        return (
                            <span className="text-sm">
                                {usable} / {harvested}
                            </span>
                        );
                    },
                },
                {
                    header: "Credit",
                    priority: 5,
                    renderCell: (core: any) => {
                        if (!core.core_credit_value) return "—";
                        return (
                            <span className={core.core_credit_issued ? "text-green-600" : ""}>
                                ${parseFloat(core.core_credit_value).toFixed(2)}
                                {core.core_credit_issued && " (Issued)"}
                            </span>
                        );
                    },
                },
            ]}
            renderActions={(core) => <CoreActionsCell core={core} />}
            onCreate={() => navigate({ to: "/reman/cores/receive" })}
        />
    );
}

export default CoresEditorPage;
