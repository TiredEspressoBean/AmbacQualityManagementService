import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentTypeActionsCell } from "@/components/edit-equipment-type-action-cell.tsx";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

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
        queryFn: () => api["api_Equipment_types_list"](DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "EquipmentTypes", "Equipment-types"],
        queryFn: () => api["api_Equipment-types_metadata_retrieve"](),
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
                { header: "ID", renderCell: (equipment: any) => equipment.id, priority: 1 },
                { header: "Name", renderCell: (equipment: any) => equipment.name, priority: 1 },
                { header: "Description", renderCell: (equipment: any) => equipment.description || "-", priority: 5 },
                { header: "Created", renderCell: (equipment: any) => equipment.created_at ? new Date(equipment.created_at).toLocaleDateString() : "-", priority: 4 },
                { header: "Updated", renderCell: (equipment: any) => equipment.updated_at ? new Date(equipment.updated_at).toLocaleDateString() : "-", priority: 4 },
            ]}
            renderActions={(equipmentType) => <EditEquipmentTypeActionsCell equipmentTypeId={equipmentType.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
