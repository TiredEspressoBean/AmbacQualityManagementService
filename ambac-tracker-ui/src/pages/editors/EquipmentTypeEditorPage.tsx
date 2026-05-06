import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentTypeActionsCell } from "@/components/edit-equipment-type-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"EquipmentType">>();

// Default params that match what useEquipmentTypesList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchEquipmentTypesEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["equipment-types", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Equipment_types_list({ queries: DEFAULT_LIST_PARAMS }),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "EquipmentTypes", "Equipment-types"],
        queryFn: () => api.api_Equipment_types_metadata_retrieve(),
    });
};

// Matches Django filter fields exactly
function useEquipmentTypesList({
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
    return useRetrieveEquipmentTypes({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function EquipmentTypeEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Equipment Types"
            modelName="EquipmentTypes"
            showDetailsLink={true}
            useList={useEquipmentTypesList}
            columns={[
                col({ header: "ID", renderCell: (equipment) => equipment.id, priority: 1 }),
                col({ header: "Name", renderCell: (equipment) => equipment.name, priority: 1 }),
                col({ header: "Description", renderCell: (equipment) => equipment.description || "-", priority: 5 }),
                col({ header: "Created", renderCell: (equipment) => equipment.created_at ? new Date(equipment.created_at).toLocaleDateString() : "-", priority: 4 }),
                col({ header: "Updated", renderCell: (equipment) => equipment.updated_at ? new Date(equipment.updated_at).toLocaleDateString() : "-", priority: 4 }),
            ]}
            renderActions={(equipmentType) => <EditEquipmentTypeActionsCell equipmentTypeId={equipmentType.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
