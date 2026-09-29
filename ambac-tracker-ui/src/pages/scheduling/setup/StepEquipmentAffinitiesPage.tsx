import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import {
    STEP_AFFINITIES_KEY, useDeleteStepAffinity, useStepAffinities, type StepEquipmentAffinity,
} from "@/hooks/useSchedulingSetup";
import { AFFINITY_LABEL, RowActions, toastApiError, useAllows } from "./shared";

const col = createColumnHelper<StepEquipmentAffinity>();

function useAffinitiesList({ offset, limit, ordering, search, filters }: {
    offset: number; limit: number; ordering?: string; search?: string;
    filters?: Record<string, string>;
}) {
    return useStepAffinities({ ...filters, offset, limit, ordering, search });
}

export function StepEquipmentAffinitiesPage() {
    const navigate = useNavigate();
    const allows = useAllows();
    const del = useDeleteStepAffinity();

    return (
        <ModelEditorPage
            title="Machine Eligibility"
            modelName="StepEquipmentAffinities"
            listQueryKey={[STEP_AFFINITIES_KEY]}
            useList={useAffinitiesList}
            showDetailsLink={false}
            sortOptions={[
                { label: "Machine (A-Z)", value: "equipment__name" },
                { label: "Step (A-Z)", value: "step__name" },
                { label: "Affinity", value: "affinity" },
            ]}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    Which machines can run a step, and how well. A machine's own cycle time,
                    when set, overrides the step's standard cycle on that machine.
                </p>
            }
            columns={[
                col({ header: "Machine", priority: 1, renderCell: (a) => <span className="font-medium">{a.equipment_name}</span> }),
                col({ header: "Step", priority: 1, renderCell: (a) => a.step_name }),
                col({
                    header: "Affinity",
                    priority: 1,
                    renderCell: (a) => (
                        <Badge variant={a.affinity === "eligible" ? "secondary" : "default"}>
                            {AFFINITY_LABEL[a.affinity ?? "eligible"] ?? a.affinity}
                        </Badge>
                    ),
                }),
                col({
                    header: "Cycle override",
                    priority: 2,
                    renderCell: (a) => a.cycle_time_override == null
                        ? <span className="text-muted-foreground">Step standard</span>
                        : `${a.cycle_time_override} min`,
                }),
            ]}
            renderActions={(a) => (
                <RowActions
                    label={`${a.equipment_name} for ${a.step_name}`}
                    editTo={`/production/step-equipment-affinities/${a.id}/edit`}
                    canEdit={allows("change_stepequipmentaffinity")}
                    canDelete={allows("delete_stepequipmentaffinity")}
                    onDelete={() => del.mutate(a.id, {
                        onSuccess: () => toast.success("Eligibility deleted"),
                        onError: (e) => toastApiError(e),
                    })}
                />
            )}
            onCreate={() => navigate({ to: "/production/step-equipment-affinities/new" })}
        />
    );
}
