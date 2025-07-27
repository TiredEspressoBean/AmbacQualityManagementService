import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditPartActionsCell} from "@/components/edit-parts-action-cell.tsx";

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
        queries: {
            offset,
            limit,
            ordering,
            archived: false,
            search,
        },
    });
}

export function PartsEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Parts"
            useList={usePartsList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "ERP ID (A-Z)", value: "ERP_id" },
                { label: "ERP ID (Z-A)", value: "-ERP_id" },
            ]}
            columns={[
                { header: "ERP ID", renderCell: (p: any) => p.ERP_id },
                { header: "Status", renderCell: (p: any) => p.part_status },
                { header: "Step", renderCell: (p: any) => p.step_name || p.step_description }, // depending on serialization
                { header: "Part Type", renderCell: (p: any) => p.part_type_name || p.part_type },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString() },
            ]}
            renderActions={(part) => <EditPartActionsCell partId={part.id} />}
            onCreate={() => navigate({ to: "/PartForm/create" })}
        />
    );
}
