import { useRetrievePartTypes, partTypesOptions, partTypesMetadataOptions } from "@/hooks/useRetrievePartTypes";
import { useNavigate } from "@tanstack/react-router";
import {ModelEditorPage, createColumnHelper} from "@/pages/editors/ModelEditorPage.tsx";
import {EditPartTypeActionsCell} from "@/components/edit-part-type-action-cell.tsx";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"PartTypes">>();

// Default params that match what usePartTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchPartTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(partTypesOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(partTypesMetadataOptions());
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
                col({ header: "Name", renderCell: (p) => p.name, priority: 1 }),
                col({ header: "ID prefix", renderCell: (p) => p.ID_prefix, priority: 1 }),
                col({ header: "Version", renderCell: (p) => p.version || "-", priority: 2 }),
                col({ header: "Updated At", renderCell: (p) => new Date(p.updated_at).toLocaleString(), priority: 4 }),
                col({ header: "Created At", renderCell: (p) => new Date(p.created_at).toLocaleString(), priority: 4 }),
                col({ header: "Previous Version", renderCell: (p) => p.previous_version || "-", priority: 5 }),
            ]}
            renderActions={(partType) => <EditPartTypeActionsCell partTypeId={partType.id} />}
            onCreate={() => navigate({ to: "/PartTypeForm/create" })}
        />
    );
}
