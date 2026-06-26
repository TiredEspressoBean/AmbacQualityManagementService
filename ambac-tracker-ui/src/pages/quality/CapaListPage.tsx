import { useState } from "react";
import { useListCapas } from "@/hooks/useListCapas";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { asUserInfo } from "@/lib/extended-types";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditCapaActionsCell } from "@/components/edit-capa-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { CapaStatsCards } from "@/components/capa-stats-cards";
import { Button } from "@/components/ui/button";
import { FileSignature } from "lucide-react";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"CAPA">>();

// Custom wrapper hook with filter support. URL filters (supplier, capa_type) let
// other pages deep-link into a scoped list — e.g. a supplier scorecard → its SCARs.
function useCapasListWithFilter(urlFilters: { supplier?: string; capa_type?: string }) {
    return function useCapasList({
        offset,
        limit,
        ordering,
        search,
    }: {
        offset: number;
        limit: number;
        ordering?: string;
        search?: string;
        filters?: Record<string, string>;
    }) {
        const queries: Parameters<typeof useListCapas>[0] = {
            offset,
            limit,
        };
        if (ordering !== undefined) queries.ordering = ordering;
        if (search !== undefined) queries.search = search;
        if (urlFilters.supplier) queries.supplier = urlFilters.supplier;
        if (urlFilters.capa_type) queries.capa_type = urlFilters.capa_type as never;
        return useListCapas(queries);
    };
}

export function CapaListPage() {
    const navigate = useNavigate();
    const search = useSearch({ strict: false }) as { supplier?: string; capa_type?: string };
    const [needsMyApproval, setNeedsMyApproval] = useState(false);

    const filterToolbar = (
        <Button
            variant={needsMyApproval ? "default" : "outline"}
            size="sm"
            onClick={() => setNeedsMyApproval(!needsMyApproval)}
            className="gap-2"
        >
            <FileSignature className="h-4 w-4" />
            Needs My Approval
        </Button>
    );

    return (
        <ModelEditorPage
            title="CAPAs"
            modelName="CAPA"
            headerContent={<CapaStatsCards filters={{ supplier: search.supplier, capa_type: search.capa_type }} />}
            extraToolbarContent={filterToolbar}
            useList={useCapasListWithFilter({ supplier: search.supplier, capa_type: search.capa_type })}
            sortOptions={[
                { label: "CAPA # (Newest)", value: "-capa_number" },
                { label: "CAPA # (Oldest)", value: "capa_number" },
                { label: "Due Date (Soonest)", value: "due_date" },
                { label: "Due Date (Latest)", value: "-due_date" },
                { label: "Severity (Critical First)", value: "-severity" },
                { label: "Severity (Minor First)", value: "severity" },
                { label: "Status", value: "status" },
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
            ]}
            columns={[
                col({
                    header: "CAPA #",
                    renderCell: (capa) => (
                        <span className="font-mono font-medium">{capa.capa_number}</span>
                    ),
                }),
                col({
                    header: "Type",
                    renderCell: (capa) => capa.capa_type_display,
                }),
                col({
                    header: "Problem",
                    renderCell: (capa) => (
                        <span className="max-w-[300px] truncate block" title={capa.problem_statement}>
                            {capa.problem_statement}
                        </span>
                    ),
                }),
                col({
                    header: "Status",
                    renderCell: (capa) => (
                        <StatusBadge status={capa.status} label={capa.status_display} />
                    ),
                }),
                col({
                    header: "Severity",
                    renderCell: (capa) => (
                        <StatusBadge status={capa.severity} label={capa.severity_display} />
                    ),
                }),
                col({
                    header: "Due Date",
                    renderCell: (capa) => {
                        if (!capa.due_date) return <span className="text-muted-foreground">—</span>;
                        const isOverdue = capa.is_overdue;
                        return (
                            <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                {new Date(capa.due_date).toLocaleDateString()}
                                {isOverdue && " (Overdue)"}
                            </span>
                        );
                    },
                }),
                col({
                    header: "Progress",
                    renderCell: (capa) => (
                        <span>{capa.completion_percentage}%</span>
                    ),
                }),
                col({
                    header: "Assigned To",
                    renderCell: (capa) => {
                        const info = asUserInfo(capa.assigned_to_info);
                        return info?.username || info?.email || <span className="text-muted-foreground">Unassigned</span>;
                    },
                }),
            ]}
            renderActions={(capa) => <EditCapaActionsCell capaId={capa.id} />}
            onCreate={() => navigate({ to: "/quality/capas/new" })}
            showDetailsLink={false}
        />
    );
}