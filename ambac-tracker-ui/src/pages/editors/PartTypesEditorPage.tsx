import {useRetrievePartTypes} from "@/hooks/useRetrievePartTypes";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage} from "@/pages/editors/ModelEditorPage.tsx";
import {EditPartTypeActionsCell} from "@/components/edit-part-type-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what usePartTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchPartTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["part-type", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_PartTypes_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "PartTypes", "PartTypes"],
        queryFn: () => api.api_PartTypes_metadata_retrieve(),
    });
};

// Custom wrapper hook for consistent usage
function usePartTypesList({
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

    return useRetrievePartTypes({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    })
}

export function PartTypesEditorPage() {
    const navigate = useNavigate();
    return (
        <ModelEditorPage
            title="Part Types"
            modelName="PartTypes"
            showDetailsLink={true}
            useList={usePartTypesList}
            columns={[
                { header: "Name", renderCell: (p: any) => p.name, priority: 1 },
                { header: "ID prefix", renderCell: (p: any) => p.ID_prefix, priority: 1 },
                { header: "Version", renderCell: (p: any) => p.version || "-", priority: 2 },
                { header: "Updated At", renderCell: (p: any) => new Date(p.updated_at).toLocaleString(), priority: 4 },
                { header: "Created At", renderCell: (p: any) => new Date(p.created_at).toLocaleString(), priority: 4 },
                { header: "Previous Version", renderCell: (p: any) => p.previous_version_name || "-", priority: 5 },
            ]}
            renderActions={(partType) => <EditPartTypeActionsCell partTypeId={partType.id} />}
            onCreate={() => navigate({ to: "/PartTypeForm/create" })}
        />
    );
}
