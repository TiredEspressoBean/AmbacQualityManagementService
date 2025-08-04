import { useRetrieveEquipmentTypes } from "@/hooks/useRetrieveEquipmentTypes.ts";
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage } from "@/pages/editors/ModelEditorPage.tsx";
import { EditEquipmentTypeActionsCell } from "@/components/edit-equipment-type-action-cell.tsx";

// Matches Django filter fields exactly
function useEquipmentTypesList({
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
    return useRetrieveEquipmentTypes({
        queries: {
            offset,
            limit,
            ordering,
            search,
        },
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
            sortOptions={[
                { label: "Name (A-Z)", value: "name" },
                { label: "Name (Z-A)", value: "-name" },
            ]}
            columns={[
                { header: "Name", renderCell: (equipment: any) => equipment.name },
            ]}
            renderActions={(equipmentType) => <EditEquipmentTypeActionsCell equipmentTypeId={equipmentType.id} />}
            onCreate={() => navigate({ to: "/EquipmentForm/create" })}
        />
    );
}
