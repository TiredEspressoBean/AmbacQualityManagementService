import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { QaQuarantineActionsCell } from "@/components/qa-quarantine-actions-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Parts">>();

// Custom wrapper hook for consistent usage
function usePartsList({
                          offset,
                          limit,
                          ordering,
                          search,
                          filters,
                      }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    filters?: Record<string, string>;
}) {
    // Build the queries object incrementally so optional fields are simply
    // absent rather than `key: undefined` — `exactOptionalPropertyTypes: true`
    // rejects the latter when assigning into the strict openapi-typescript
    // queries shape.
    const queries: Parameters<typeof useRetrieveParts>[0] = {
        offset,
        limit,
        archived: false,
        status__in: [
            "AWAITING_QA",
            "QUARANTINED",
            "REWORK_NEEDED",
            "REWORK_IN_PROGRESS",
        ],
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveParts(queries);
}

export function QaQuarantinePage() {
    return (
        <ModelEditorPage
            title="Quarantined Parts"
            modelName="Parts"
            showDetailsLink={true}
            useList={usePartsList}
            sortOptions={[
                { label: "Created (Newest)", value: "-created_at" },
                { label: "Created (Oldest)", value: "created_at" },
                { label: "ERP ID (A-Z)", value: "ERP_id" },
                { label: "ERP ID (Z-A)", value: "-ERP_id" },
            ]}
            columns={[
                col({ header: "ERP ID", renderCell: (p) => p.ERP_id }),
                col({ header: "Status", renderCell: (p) => <StatusBadge status={p.part_status} size="sm" /> }),
                col({ header: "Step", renderCell: (p) => p.step_name ?? "—" }),
                col({ header: "Part Type", renderCell: (p) => p.part_type_name ?? p.part_type }),
                col({ header: "Created At", renderCell: (p) => new Date(p.created_at).toLocaleString() }),
            ]}
            renderActions={(part) => <QaQuarantineActionsCell part={part} />}
        />
    );
}
