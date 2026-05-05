import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditPartActionsCell } from "@/components/edit-parts-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Parts } from "@/lib/api/types";

const col = createColumnHelper<Parts>();

// Default params that match what usePartsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    archived: false,
    search: "",
};

// Prefetch function for route loader
export const prefetchPartsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["part", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Parts_list({ queries: DEFAULT_LIST_PARAMS }),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Parts", "Parts"],
        queryFn: () => api.api_Parts_metadata_retrieve(),
    });
};

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
    // Build queries incrementally so optional fields are absent rather
    // than `key: undefined` — exactOptionalPropertyTypes is strict.
    const queries: Parameters<typeof useRetrieveParts>[0] = {
        offset,
        limit,
        archived: false,
        ...filters,
    };
    if (ordering !== undefined) queries.ordering = ordering;
    if (search !== undefined) queries.search = search;
    return useRetrieveParts(queries);
}

export function PartsEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Parts"
            modelName="Parts"
            showDetailsLink={true}
            useList={usePartsList}
            columns={[
                col({ header: "ERP ID", renderCell: (p) => p.ERP_id, priority: 1 }),
                col({ header: "Status", renderCell: (p) => <StatusBadge status={p.part_status} size="sm" />, priority: 1 }),
                col({ header: "Part Type", renderCell: (p) => p.part_type_name ?? p.part_type, priority: 2 }),
                col({ header: "Step", renderCell: (p) => p.step_name ?? "—", priority: 3 }),
                col({ header: "Created At", renderCell: (p) => new Date(p.created_at).toLocaleString(), priority: 4 }),
            ]}
            renderActions={(part) => <EditPartActionsCell partId={part.id} />}
            onCreate={() => navigate({ to: "/PartForm/create" })}
        />
    );
}
