import { useRetrieveEquipments } from "@/hooks/useRetrieveEquipments.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentActionsCell } from "@/components/edit-equipment-action-cell.tsx";

// Matches Django filter fields exactly
function useEquipmentsList({
                          offset,
                          limit,
                          ordering,
                          search,
                      }: {
    offset: number;
    limit: number;
    ordering?: string;
    search?: string;
    part_type?: string;
    process?: string;
}) {
    return useRetrieveEquipments({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
    });
}

export function EquipmentEditorPage() {
    const navigate = useNavigate();

    return (
        <ModelEditorPage
            title="Equipments"
            useList={useEquipmentsList}
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
                { label: "Equipment Type Name (A-Z)", value: "equipment_type__name" },
                { label: "Equipment Type Name (Z-A)", value: "-equipment_type__name" },
            ]}
            columns={[
                { header: "Name", renderCell: (equipment: any) => equipment.name },
                { header: "Equipment Type", renderCell: (equipment: any) => equipment.equipment_type_name },
            ]}
            renderActions={(equipment) => <EditEquipmentActionsCell equipmentId={equipment.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
