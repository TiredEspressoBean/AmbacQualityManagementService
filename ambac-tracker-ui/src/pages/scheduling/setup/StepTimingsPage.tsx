import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import {
    STEP_TIMINGS_KEY, useDeleteStepTiming, useStepTimings, type StepTiming,
} from "@/hooks/useSchedulingSetup";
import { ATTENTION_LABEL, RowActions, toastApiError, useAllows } from "./shared";

const col = createColumnHelper<StepTiming>();

const mins = (n: number | undefined) => `${n ?? 0} min`;

function useStepTimingsList({ offset, limit, ordering, search, filters }: {
    offset: number; limit: number; ordering?: string; search?: string;
    filters?: Record<string, string>;
}) {
    return useStepTimings({ ...filters, offset, limit, ordering, search });
}

export function StepTimingsPage() {
    const navigate = useNavigate();
    const allows = useAllows();
    const del = useDeleteStepTiming();

    return (
        <ModelEditorPage
            title="Step Timings"
            modelName="StepTimings"
            listQueryKey={[STEP_TIMINGS_KEY]}
            useList={useStepTimingsList}
            showDetailsLink={false}
            sortOptions={[
                { label: "Step (A-Z)", value: "step__name" },
                { label: "Step (Z-A)", value: "-step__name" },
                { label: "Cycle time (High-Low)", value: "-cycle_time_minutes" },
                { label: "Setup (High-Low)", value: "-setup_minutes" },
            ]}
            headerContent={
                <p className="text-sm text-muted-foreground">
                    A step's standard times — what the scheduler and rough-cut capacity size
                    every operation from. One row per step.
                </p>
            }
            columns={[
                col({ header: "Step", priority: 1, renderCell: (t) => <span className="font-medium">{t.step_name}</span> }),
                col({ header: "Setup", priority: 1, renderCell: (t) => mins(t.setup_minutes) }),
                col({ header: "Cycle / piece", priority: 1, renderCell: (t) => mins(t.cycle_time_minutes) }),
                col({ header: "Load / unload / piece", priority: 2, renderCell: (t) => mins(t.load_unload_per_piece) }),
                col({ header: "External setup", priority: 3, renderCell: (t) => mins(t.external_setup_minutes) }),
                col({
                    header: "Attention",
                    priority: 2,
                    renderCell: (t) => (
                        <Badge variant="secondary">{ATTENTION_LABEL[t.attention_type ?? "full"] ?? t.attention_type}</Badge>
                    ),
                }),
            ]}
            renderActions={(t) => (
                <RowActions
                    label={`timing for ${t.step_name}`}
                    editTo={`/production/step-timings/${t.id}/edit`}
                    canEdit={allows("change_steptiming")}
                    canDelete={allows("delete_steptiming")}
                    onDelete={() => del.mutate(t.id, {
                        onSuccess: () => toast.success("Step timing deleted"),
                        onError: (e) => toastApiError(e),
                    })}
                />
            )}
            onCreate={() => navigate({ to: "/production/step-timings/new" })}
        />
    );
}
