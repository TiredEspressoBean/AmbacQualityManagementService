import { toast } from "sonner";
import { ArrowRight } from "lucide-react";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import {
    CHANGEOVERS_KEY, useChangeovers, useDeleteChangeover, type WorkCenterChangeover,
} from "@/hooks/useSchedulingSetup";
import { RowActions, toastApiError, useAllows } from "./shared";

const col = createColumnHelper<WorkCenterChangeover>();

function useChangeoversList({ offset, limit, ordering, search, filters }: {
    offset: number; limit: number; ordering?: string; search?: string;
    filters?: Record<string, string>;
}) {
    return useChangeovers({ ...filters, offset, limit, ordering, search });
}

export function WorkCenterChangeoversPage() {
    const allows = useAllows();
    const del = useDeleteChangeover();

    return (
        <ModelEditorPage
            title="Changeovers"
            modelName="WorkCenterChangeovers"
            listQueryKey={[CHANGEOVERS_KEY]}
            useList={useChangeoversList}
            showDetailsLink={false}
            sortOptions={[
                { label: "Machine (A-Z)", value: "equipment__name" },
                { label: "From step (A-Z)", value: "from_step__name" },
                { label: "Minutes (High-Low)", value: "-changeover_minutes" },
            ]}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    Minutes to reconfigure a machine when it switches from running one step to
                    another. One row per machine, from step and to step, edited on the machine.
                </p>
            }
            columns={[
                col({ header: "Machine", priority: 1, renderCell: (c) => <span className="font-medium">{c.equipment_name}</span> }),
                col({
                    header: "Switch",
                    priority: 1,
                    renderCell: (c) => (
                        <span className="inline-flex items-center gap-1.5">
                            {c.from_step_name}
                            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                            {c.to_step_name}
                        </span>
                    ),
                }),
                col({ header: "Minutes", priority: 1, renderCell: (c) => <span className="tabular-nums">{c.changeover_minutes ?? 0}</span> }),
            ]}
            renderActions={(c) => (
                <RowActions
                    label={`changeover ${c.from_step_name} to ${c.to_step_name} on ${c.equipment_name}`}
                    editTo={`/EquipmentForm/edit/${c.equipment}`}
                    canEdit={allows("change_workcenterchangeover")}
                    canDelete={allows("delete_workcenterchangeover")}
                    onDelete={() => del.mutate(c.id, {
                        onSuccess: () => toast.success("Changeover deleted"),
                        onError: (e) => toastApiError(e),
                    })}
                />
            )}
        />
    );
}
