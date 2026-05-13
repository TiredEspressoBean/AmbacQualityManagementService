import { useRetrieveParts } from "@/hooks/parts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { QaPartActionsCell } from "@/components/qa-parts-actions-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Parts">>();

// Custom wrapper hook for consistent usage
function usePartsList({
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
    // Use needs_qa: true to get parts that require sampling AND haven't passed QA yet.
    // Build queries incrementally for exactOptionalPropertyTypes.
    const queries: Parameters<typeof useRetrieveParts>[0] = {
        offset,
        limit,
        archived: false,
        needs_qa: true,
        status__in: [
            "PENDING",
            "IN_PROGRESS",
            "REWORK_NEEDED",
            "REWORK_IN_PROGRESS",
            "READY_FOR_NEXT_STEP",
        ],
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveParts(queries);
}

export function QaPartsInProcessPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Parts"
            useList={usePartsList}
            modelName="Parts"
            showDetailsLink={true}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "ERP ID (A-Z)", value: "ERP_id" },
                { label: "ERP ID (Z-A)", value: "-ERP_id" },
            ]}
            columns={[
                col({ header: "ERP ID", renderCell: (p) => p.ERP_id }),
                col({ header: "Status", renderCell: (p) => <StatusBadge status={p.part_status} size="sm" /> }),
                col({ header: "WorkOrder", renderCell: (p) => p.work_order_erp_id ?? "—" }),
                col({ header: "Step", renderCell: (p) => p.step_name ?? "—" }),
                col({ header: "Process", renderCell: (p) => p.process_name }),
                col({ header: "Part Type", renderCell: (p) => p.part_type_name ?? p.part_type }),
                col({ header: "Created At", renderCell: (p) => new Date(p.created_at).toLocaleString() }),
            ]}
            renderActions={(part) => <QaPartActionsCell part={part} />}
            onCreate={() => navigate({ to: "/PartForm/create" })}
        />
    );
}
