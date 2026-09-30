import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import {
    LIFE_LIMIT_DEFINITIONS_KEY, useDeleteLifeLimitDefinition, useLifeLimitDefinitionsList,
    type LifeLimitDefinition,
} from "@/hooks/useLifeLimitDefinitionsAdmin";
import { RowActions, toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

const col = createColumnHelper<LifeLimitDefinition>();
const limit = (v: string | null | undefined) => (v == null || v === "" ? "—" : String(Number(v)));

function useList({ offset, limit: pageSize, ordering, search, filters }: {
    offset: number; limit: number; ordering?: string; search?: string; filters?: Record<string, string>;
}) {
    return useLifeLimitDefinitionsList({ ...filters, offset, limit: pageSize, ordering, search });
}

export function LifeLimitDefinitionsEditorPage() {
    const navigate = useNavigate();
    const allows = useAllows();
    const del = useDeleteLifeLimitDefinition();

    return (
        <ModelEditorPage
            title="Life Limit Definitions"
            modelName="LifeLimitDefinitions"
            listQueryKey={[LIFE_LIMIT_DEFINITIONS_KEY]}
            useList={useList}
            showDetailsLink={false}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    What a part can wear out by — cycles, hours, shelf life — and where the warning
                    and the hard stop sit. Part types pick which ones apply on their own form.
                </p>
            }
            columns={[
                col({ header: "Name", priority: 1, renderCell: (d) => <span className="font-medium">{d.name}</span> }),
                col({ header: "Unit", priority: 1, renderCell: (d) => d.unit_label || d.unit }),
                col({ header: "Soft limit", priority: 2, renderCell: (d) => <span className="tabular-nums">{limit(d.soft_limit)}</span> }),
                col({ header: "Hard limit", priority: 1, renderCell: (d) => <span className="tabular-nums">{limit(d.hard_limit)}</span> }),
                col({
                    header: "Counts",
                    priority: 3,
                    renderCell: (d) => <Badge variant="secondary">{d.is_calendar_based ? "Calendar time" : "Usage"}</Badge>,
                }),
            ]}
            renderActions={(d) => (
                <RowActions
                    label={d.name}
                    editTo={`/editor/life-limit-definitions/${d.id}/edit`}
                    canEdit={allows("change_lifelimitdefinition")}
                    canDelete={allows("delete_lifelimitdefinition")}
                    onDelete={() => del.mutate(d.id, {
                        onSuccess: () => toast.success(`${d.name} deleted`),
                        onError: (e) => toastApiError(e),
                    })}
                />
            )}
            onCreate={() => navigate({ to: "/editor/life-limit-definitions/new" })}
        />
    );
}
