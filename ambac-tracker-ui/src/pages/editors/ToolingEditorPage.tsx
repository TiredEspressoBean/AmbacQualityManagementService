// Tooling / shared-resource editor (master data) — lives in the Data Management hub.
// A fixture / cutting tool / die / NC program with a limited quantity; the scheduler
// serializes the operations that require it against the quantity available.
import { useNavigate } from "@tanstack/react-router";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { EditFixtureActionsCell } from "@/components/edit-fixture-action-cell";
import { useFixturesList } from "@/hooks/useScheduling";
import { Badge } from "@/components/ui/badge";
import type { Schema } from "@/lib/api/types";

const col = createColumnHelper<Schema<"Fixture">>();

const KIND_LABELS: Record<string, string> = {
  FIXTURE: "Fixture",
  TOOL: "Cutting tool",
  DIE: "Die / mold",
  PROGRAM: "NC program",
  OTHER: "Other",
};

export function ToolingEditorPage() {
  const navigate = useNavigate();

  return (
    <ModelEditorPage
      title="Tooling"
      modelName="Fixtures"
      showDetailsLink={false}
      useList={useFixturesList}
      columns={[
        col({ header: "Name", renderCell: (f) => f.name, priority: 1 }),
        col({
          header: "Kind",
          renderCell: (f) => <Badge variant="secondary">{KIND_LABELS[f.kind ?? "FIXTURE"] ?? f.kind}</Badge>,
          priority: 1,
        }),
        col({ header: "Quantity", renderCell: (f) => f.quantity, priority: 1 }),
        col({
          header: "Required at",
          renderCell: (f) => {
            const n = (f.step_names ?? f.steps ?? []).length;
            return n === 0 ? "—" : `${n} step${n === 1 ? "" : "s"}`;
          },
          priority: 2,
        }),
      ]}
      renderActions={(f) => <EditFixtureActionsCell fixtureId={String(f.id)} name={f.name} />}
      onCreate={() => navigate({ to: "/editor/tooling/new" })}
    />
  );
}

export default ToolingEditorPage;
