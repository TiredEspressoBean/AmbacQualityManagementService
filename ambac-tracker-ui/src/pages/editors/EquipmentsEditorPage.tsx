import { useRetrieveEquipments, equipmentsOptions, equipmentsMetadataOptions } from "@/hooks/useRetrieveEquipments.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentActionsCell } from "@/components/edit-equipment-action-cell.tsx";
import { StatusBadge } from "@/components/ui/status-badge";
import type { QueryClient } from "@tanstack/react-query";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Equipments">>();

// Default params that match what useEquipmentsList passes on initial render
const DEFAULT_LIST_PARAMS = {
    offset: 0,
    limit: 25,
    search: "",
};

// Prefetch function for route loader
export const prefetchEquipmentsEditor = (queryClient: QueryClient) => {
    queryClient.prefetchQuery(equipmentsOptions(DEFAULT_LIST_PARAMS));
    queryClient.prefetchQuery(equipmentsMetadataOptions());
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
                col({ header: "Name", renderCell: (equipment) => equipment.name, priority: 1 }),
                col({ header: "Equipment Type", renderCell: (equipment) => equipment.equipment_type_name || "—", priority: 2 }),
                col({ header: "Serial #", renderCell: (equipment) => equipment.serial_number || "—", priority: 2 }),
                col({ header: "Manufacturer", renderCell: (equipment) => equipment.manufacturer || "—", priority: 3 }),
                col({ header: "Location", renderCell: (equipment) => equipment.location || "—", priority: 3 }),
                col({
                    header: "Status",
                    renderCell: (equipment) => {
                        if (!equipment.status) return "—";
                        return <StatusBadge status={equipment.status} />;
                    },
                    priority: 1,
                }),
            ]}
            renderActions={(equipment) => <EditEquipmentActionsCell equipmentId={equipment.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
