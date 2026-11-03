import { toast } from "sonner";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MeasuredLine, SourceBadge, measuredValue, type Aspect } from "@/components/scheduling/MeasuredTiming";
import {
    STEP_TIMINGS_KEY, useDeleteStepTiming, useMeasuredStepTimings, useStepTimings, useUpdateStepTiming,
    type MeasuredStepTiming, type StepTiming,
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

function TimingCell({ authored, m, aspect }: { authored: number | undefined; m: MeasuredStepTiming | undefined; aspect: Aspect }) {
    return (
        <div className="space-y-0.5">
            <div className="flex flex-wrap items-center gap-1.5">
                {mins(authored)}
                <SourceBadge source={aspect === "setup" ? m?.setup_in_use : m?.cycle_in_use} />
            </div>
            <MeasuredLine m={m} aspect={aspect} />
        </div>
    );
}

export function StepTimingsPage() {
    const allows = useAllows();
    const del = useDeleteStepTiming();
    const update = useUpdateStepTiming();
    const { data: measuredRows } = useMeasuredStepTimings();
    const measured = new Map((measuredRows ?? []).map((m) => [m.step, m]));

    /** Copy the measured setup / cycle into the authored timing — an ordinary edit. */
    function applyMeasured(t: StepTiming) {
        const m = measured.get(t.step);
        const setup = measuredValue(m, "setup");
        const cycle = measuredValue(m, "cycle");
        const data: { setup_minutes?: number; cycle_time_minutes?: number } = {};
        if (setup != null && setup !== t.setup_minutes) data.setup_minutes = setup;
        if (cycle != null && cycle !== t.cycle_time_minutes) data.cycle_time_minutes = cycle;
        update.mutate({ id: t.id, data }, {
            onSuccess: () => toast.success(`Measured times saved to ${t.step_name}`),
            onError: (e) => toastApiError(e),
        });
    }

    function differs(t: StepTiming) {
        const m = measured.get(t.step);
        const setup = measuredValue(m, "setup");
        const cycle = measuredValue(m, "cycle");
        return (setup != null && setup !== t.setup_minutes) || (cycle != null && cycle !== t.cycle_time_minutes);
    }

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
                    every operation from. One row per step, edited on the step. Beside each,
                    what the step records measure over the last year (first-pass work only,
                    hold and outside-processing time left out) and which one the scheduler
                    uses: an authored time wins; an unset one falls back to the measurement.
                </p>
            }
            columns={[
                col({ header: "Step", priority: 1, renderCell: (t) => <span className="font-medium">{t.step_name}</span> }),
                col({ header: "Setup", priority: 1, renderCell: (t) => <TimingCell authored={t.setup_minutes} m={measured.get(t.step)} aspect="setup" /> }),
                col({ header: "Cycle / piece", priority: 1, renderCell: (t) => <TimingCell authored={t.cycle_time_minutes} m={measured.get(t.step)} aspect="cycle" /> }),
                col({ header: "Load / unload / piece", priority: 2, renderCell: (t) => mins(t.load_unload_per_piece) }),
                col({ header: "External setup", priority: 3, renderCell: (t) => mins(t.external_setup_minutes) }),
                col({
                    header: "Measured",
                    priority: 2,
                    renderCell: (t) => allows("change_steptiming") && differs(t) ? (
                        <Button size="sm" variant="outline" disabled={update.isPending} onClick={() => applyMeasured(t)}>
                            Use measured
                        </Button>
                    ) : null,
                }),
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
                    editTo={`/editor/steps/${t.step}/edit`}
                    canEdit={allows("change_steptiming")}
                    canDelete={allows("delete_steptiming")}
                    onDelete={() => del.mutate(t.id, {
                        onSuccess: () => toast.success("Step timing deleted"),
                        onError: (e) => toastApiError(e),
                    })}
                />
            )}
        />
    );
}
