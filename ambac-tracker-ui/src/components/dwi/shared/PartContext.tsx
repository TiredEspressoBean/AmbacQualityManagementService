/**
 * Optional runtime context that binds a `Part` (and its owning Work Order
 * + the inspection's pending `QualityReports` id, if any) to substep
 * nodes that need them — currently `PartAnnotation`.
 *
 * Authoring surfaces don't provide this context, so the consuming nodes
 * fall back to a "placeholder — operator will see the real widget" state.
 * The operator runtime page wraps the editor in this provider with the
 * actual ids before render.
 */
import { createContext, useContext } from "react";

export type PartContextValue = {
    part_id?: string | number | null;
    work_order_id?: string | number | null;
    /** Pending QualityReports id created for this substep's inspection
     *  event, when `is_inspection_point=True`. Annotations created via
     *  PartAnnotation get linked to this report. */
    quality_report_id?: string | number | null;
    /** The current StepExecution id for the part. Needed by
     *  measurement-bound capture nodes (e.g. ComputedValue variables
     *  with source=measurement_definition) to query existing
     *  `StepExecutionMeasurement` rows and pre-fill themselves. */
    step_execution_id?: string | number | null;
};

export const PartContext = createContext<PartContextValue | null>(null);

export function usePartContext(): PartContextValue {
    return useContext(PartContext) ?? {};
}
