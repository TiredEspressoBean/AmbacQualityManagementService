// Purchased-material editor (master data) — the BUY side of a BOM.
// PartTypes are in-house SKUs (things you make); Materials are purchased components
// (O-rings, seals, coils) with a supplier and a purchase lead time.
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditMaterialActionsCell } from "@/components/edit-material-action-cell";
import { useMaterialsList } from "@/hooks/useMaterials";
import { Badge } from "@/components/ui/badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Material">>();

export function MaterialsEditorPage() {
  const navigate = useNavigate();

  return (
    <ModelEditorPage
      title="Materials"
      modelName="Materials"
      showDetailsLink={false}
      useList={useMaterialsList}
      columns={[
        col({ header: "Name", renderCell: (m) => m.name, priority: 1 }),
        col({ header: "Part number", renderCell: (m) => m.part_number || "—", priority: 2 }),
        col({ header: "UoM", renderCell: (m) => m.unit_of_measure || "—", priority: 3 }),
        col({
          header: "Lead time",
          renderCell: (m) => (m.purchase_lead_time_days == null ? "—" : `${m.purchase_lead_time_days}d`),
          priority: 1,
        }),
        col({
          header: "Supplier",
          renderCell: (m) => m.preferred_supplier_name || "—",
          priority: 2,
        }),
        col({
          header: "Status",
          renderCell: (m) =>
            m.is_active ? (
              <Badge variant="secondary">Active</Badge>
            ) : (
              <Badge variant="outline">Inactive</Badge>
            ),
          priority: 1,
        }),
      ]}
      renderActions={(m) => <EditMaterialActionsCell materialId={String(m.id)} name={m.name} />}
      onCreate={() => navigate({ to: "/editor/materials/new" })}
    />
  );
}

export default MaterialsEditorPage;
