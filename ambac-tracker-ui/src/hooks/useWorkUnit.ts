import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { ensureStepExecution, TrainingGateError } from "@/hooks/useEnsureStepExecution";

/**
 * Open one unit in the DWI operator runtime — the directions for its current step and
 * the capture for it.
 *
 * A reman core is a PART (Documents/CORE_AS_PART_DESIGN.md), so teardown and rebuild
 * run on the same runtime as any part; this is the one launcher every reman page uses
 * rather than the old standalone disassembly screen. It looks the unit up by its part,
 * ensures the step execution for the step it is at, and routes into the runtime.
 *
 * When the operator is not cleared for the step, it does NOT try to handle the override
 * itself: it sends them to the work order's Start Work flow, which already carries the
 * training gate and the supervisor-override path.
 */
export function useWorkUnit() {
    const navigate = useNavigate();
    const [pending, setPending] = useState(false);

    const workUnit = async (partId: string, workOrderId: string) => {
        setPending(true);
        try {
            const part = await api.api_Parts_retrieve({ params: { id: partId } });
            const stepId = part.step ? String(part.step) : null;
            if (!stepId) {
                toast.error("This unit has no current step yet — plan or start its teardown first.");
                return;
            }
            const { executionId } = await ensureStepExecution({ partId, stepId });
            navigate({
                to: "/operator/steps/$stepId/substeps",
                params: { stepId },
                search: { part: partId, workOrder: workOrderId, execution: executionId, at: 0 },
            });
        } catch (e) {
            if (e instanceof TrainingGateError) {
                toast.error("You're not cleared for this step. Start it from the work order, where a supervisor can authorise it.");
                navigate({ to: "/workorder/$workOrderId", params: { workOrderId } });
                return;
            }
            toast.error(e instanceof Error ? e.message : "Could not open this unit.");
        } finally {
            setPending(false);
        }
    };

    return { workUnit, pending };
}
