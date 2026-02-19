import { useState } from "react";
import { useListCapas } from "@/hooks/useListCapas";
import { useNavigate } from "@tanstack/react-router";
import { asUserInfo } from "@/lib/extended-types";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage";
import { EditCapaActionsCell } from "@/components/edit-capa-action-cell";
import { StatusBadge } from "@/components/ui/status-badge";
import { CapaStatsCards } from "@/components/capa-stats-cards";
import { Button } from "@/components/ui/button";
import { FileSignature } from "lucide-react";

// Custom wrapper hook with filter support
function useCapasListWithFilter(needsMyApproval: boolean) {
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
    }) {
        return useListCapas({
            queries: {
                offset,
                limit,
                ordering,
                search,
                needs_my_approval: needsMyApproval ? true : undefined,
            } as any,
        });
    };
}

export function CapaListPage() {
    const navigate = useNavigate();
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
            headerContent={<CapaStatsCards />}
            extraToolbarContent={filterToolbar}
            useList={useCapasListWithFilter(needsMyApproval)}
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
                {
                    header: "CAPA #",
                    renderCell: (capa: any) => (
                        <span className="font-mono font-medium">{capa.capa_number}</span>
                    ),
                },
                {
                    header: "Type",
                    renderCell: (capa: any) => capa.capa_type_display,
                },
                {
                    header: "Problem",
                    renderCell: (capa: any) => (
                        <span className="max-w-[300px] truncate block" title={capa.problem_statement}>
                            {capa.problem_statement}
                        </span>
                    ),
                },
                {
                    header: "Status",
                    renderCell: (capa: any) => (
                        <StatusBadge status={capa.status} label={capa.status_display} />
                    ),
                },
                {
                    header: "Severity",
                    renderCell: (capa: any) => (
                        <StatusBadge status={capa.severity} label={capa.severity_display} />
                    ),
                },
                {
                    header: "Due Date",
                    renderCell: (capa: any) => {
                        if (!capa.due_date) return <span className="text-muted-foreground">—</span>;
                        const isOverdue = capa.is_overdue;
                        return (
                            <span className={isOverdue ? "text-destructive font-medium" : ""}>
                                {new Date(capa.due_date).toLocaleDateString()}
                                {isOverdue && " (Overdue)"}
                            </span>
                        );
                    },
                },
                {
                    header: "Progress",
                    renderCell: (capa: any) => (
                        <span>{capa.completion_percentage}%</span>
                    ),
                },
                {
                    header: "Assigned To",
                    renderCell: (capa: any) => {
                        const info = asUserInfo(capa.assigned_to_info);
                        return info?.username || info?.email || <span className="text-muted-foreground">Unassigned</span>;
                    },
                },
            ]}
            renderActions={(capa) => <EditCapaActionsCell capaId={capa.id} />}
            onCreate={() => navigate({ to: "/quality/capas/new" })}
            showDetailsLink={false}
        />
    );
}