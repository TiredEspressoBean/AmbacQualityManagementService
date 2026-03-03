import { useRetrieveHarvestedComponents } from "@/hooks/useRetrieveHarvestedComponents";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Package, Trash2, Eye, Link as LinkIcon } from "lucide-react";
import { Link } from "@tanstack/react-router";

// Default params
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchHarvestedComponents = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["harvested-components", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_HarvestedComponents_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "HarvestedComponents", "HarvestedComponents"],
        queryFn: () => api.api_HarvestedComponents_metadata_retrieve(),
    });
};

// Custom wrapper hook
function useComponentsList({
    offset, limit, ordering, search, filters,
}: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    return useRetrieveHarvestedComponents({
        offset, limit, ordering, search, ...filters,
    });
}

// Condition grade color mapping
function getConditionVariant(grade: string): "default" | "secondary" | "destructive" | "outline" {
    switch (grade) {
        case 'A': return 'default';
        case 'B': return 'secondary';
        case 'C': return 'outline';
        case 'SCRAP': return 'destructive';
        default: return 'outline';
    }
}

// Actions cell component
function ComponentActionsCell({ component }: { component: any }) {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreHorizontal className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                    <Link to={`/reman/cores/${component.core}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Source Core
                    </Link>
                </DropdownMenuItem>
                {component.component_part && (
                    <DropdownMenuItem asChild>
                        <Link to={`/details/Parts/${component.component_part}`}>
                            <LinkIcon className="mr-2 h-4 w-4" />
                            View Part Record
                        </Link>
                    </DropdownMenuItem>
                )}
                {!component.is_scrapped && !component.component_part && (
                    <>
                        <DropdownMenuItem>
                            <Package className="mr-2 h-4 w-4" />
                            Accept to Inventory
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                            <Trash2 className="mr-2 h-4 w-4" />
                            Scrap Component
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

export function HarvestedComponentsPage() {
    return (
        <ModelEditorPage
            title="Harvested Components"
            modelName="HarvestedComponents"
            showDetailsLink={false}
            useList={useComponentsList}
            columns={[
                {
                    header: "Component Type",
                    priority: 1,
                    renderCell: (component: any) => (
                        <span className="font-medium">{component.component_type_name}</span>
                    ),
                },
                {
                    header: "Source Core",
                    priority: 1,
                    renderCell: (component: any) => (
                        <Link
                            to={`/reman/cores/${component.core}`}
                            className="font-mono text-primary hover:underline"
                        >
                            {component.core_number}
                        </Link>
                    ),
                },
                {
                    header: "Position",
                    priority: 3,
                    renderCell: (component: any) => component.position || "—",
                },
                {
                    header: "Condition",
                    priority: 2,
                    renderCell: (component: any) => {
                        const grade = component.condition_grade;
                        if (!grade) return "—";
                        return (
                            <Badge variant={getConditionVariant(grade)}>
                                Grade {grade}
                            </Badge>
                        );
                    },
                },
                {
                    header: "Status",
                    priority: 1,
                    renderCell: (component: any) => {
                        if (component.is_scrapped) {
                            return <Badge variant="destructive">Scrapped</Badge>;
                        }
                        if (component.component_part) {
                            return <Badge variant="default">In Inventory</Badge>;
                        }
                        return <Badge variant="secondary">Pending</Badge>;
                    },
                },
                {
                    header: "Part ID",
                    priority: 2,
                    renderCell: (component: any) => {
                        if (component.component_part_erp_id) {
                            return (
                                <Link
                                    to={`/details/Parts/${component.component_part}`}
                                    className="font-mono text-primary hover:underline"
                                >
                                    {component.component_part_erp_id}
                                </Link>
                            );
                        }
                        return "—";
                    },
                },
                {
                    header: "Harvested",
                    priority: 3,
                    renderCell: (component: any) =>
                        component.disassembled_at
                            ? format(new Date(component.disassembled_at), "MMM d, yyyy")
                            : "—",
                },
                {
                    header: "By",
                    priority: 4,
                    renderCell: (component: any) => component.disassembled_by_name || "—",
                },
            ]}
            renderActions={(component) => <ComponentActionsCell component={component} />}
        />
    );
}

export default HarvestedComponentsPage;
