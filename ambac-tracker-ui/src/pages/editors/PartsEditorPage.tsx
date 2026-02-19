import { useRetrieveParts } from "@/hooks/useRetrieveParts";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditPartActionsCell} from "@/components/edit-parts-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

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
        queryFn: () => api.api_Parts_list(DEFAULT_LIST_PARAMS),
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
    return useRetrieveParts({
        offset,
        limit,
        ordering,
        archived: false,
        search,
        ...filters,
    });
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
                { header: "ERP ID", renderCell: (p: any) => p.ERP_id, priority: 1 },
                { header: "Status", renderCell: (p: any) => p.part_status, priority: 1 },
                { header: "Part Type", renderCell: (p: any) => p.part_type_name || p.part_type, priority: 2 },
                { header: "Step", renderCell: (p: any) => p.step_name || p.step_description, priority: 3 },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString(), priority: 4 },
            ]}
            renderActions={(part) => <EditPartActionsCell partId={part.id} />}
            onCreate={() => navigate({ to: "/PartForm/create" })}
        />
    );
}
