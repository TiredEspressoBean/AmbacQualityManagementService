import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {QaPartActionsCell} from "@/components/qa-parts-actions-cell.tsx";

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
    return useRetrieveParts({
        offset,
        limit,
        ordering,
        search,
        archived: false,
        requires_sampling: true,
        status__in: [
            "PENDING",
            "IN_PROGRESS",
            "REWORK_NEEDED",
            "REWORK_IN_PROGRESS",
        ],
    });
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
                { header: "ERP ID", renderCell: (p: any) => p.ERP_id },
                { header: "Status", renderCell: (p: any) => p.part_status },
                { header: "WorkOrder", renderCell:(p:any) => p.work_order_erp_id || "-"},
                { header: "Step", renderCell: (p: any) => p.step_name || p.step_description }, // depending on serialization
                {header: "Process", renderCell: (p:any) => p.process_name},
                { header: "Part Type", renderCell: (p: any) => p.part_type_name || p.part_type },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString() },
            ]}
            renderActions={(part) => <QaPartActionsCell part={part} />}
            onCreate={() => navigate({ to: "/PartForm/create" })}
        />
    );
}
