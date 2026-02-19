import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentActionsCell } from "@/components/edit-equipment-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import { api } from "@/lib/api/generated";
import type { QueryClient } from "@tanstack/react-query";

// Default params that match what useEquipmentsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchEquipmentsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery({
        queryKey: ["equipment", DEFAULT_LIST_PARAMS],
        queryFn: () => api.api_Equipment_list(DEFAULT_LIST_PARAMS),
    });
    queryClient.prefetchQuery({
        queryKey: ["metadata", "Equipments", "Equipment"],
        queryFn: () => api.api_Equipment_metadata_retrieve(),
    });
};

// Matches Django filter fields exactly
function useEquipmentsList({
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
    return useRetrieveEquipments({
        offset,
        limit,
        ordering,
        search,
        ...filters,
    });
}

export function EquipmentEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Equipments"
            modelName="Equipments"
            showDetailsLink={true}
            useList={useEquipmentsList}
            columns={[
                { header: "Name", renderCell: (equipment: any) => equipment.name, priority: 1 },
                { header: "Equipment Type", renderCell: (equipment: any) => equipment.equipment_type_name || "—", priority: 2 },
                { header: "Serial #", renderCell: (equipment: any) => equipment.serial_number || "—", priority: 2 },
                { header: "Manufacturer", renderCell: (equipment: any) => equipment.manufacturer || "—", priority: 3 },
                { header: "Location", renderCell: (equipment: any) => equipment.location || "—", priority: 3 },
                {
                    header: "Status",
                    renderCell: (equipment: any) => {
                        if (!equipment.status) return "—";
                        return <StatusBadge status={equipment.status} />;
                    },
                    priority: 1,
                },
            ]}
            renderActions={(equipment) => <EditEquipmentActionsCell equipmentId={equipment.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
