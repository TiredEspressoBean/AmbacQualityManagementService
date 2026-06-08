import { createContext, useContext } from "react";

/** Operator capture store.
 *
 * When the editor renders in `editable: false` mode (the right preview pane
 * or the operator runtime), capture-node form fields become real interactive
 * inputs. Their values land in this context, keyed by each node's stable
 * `node_id`. The editor JSON itself is never mutated — the substep document
 * stays the engineer's template.
 *
 * In production this routes to the backend (`SubstepResponse`,
 * `SubstepGateCompletion`, `StepExecutionMeasurement`). The spike + preview
 * uses local React state so the data flow is visible end-to-end. */

export type OperatorResponses = Record<string, unknown>;

export type OperatorResponseContextValue = {
    responses: OperatorResponses;
    setResponse: (node_id: string, value: unknown) => void;
};

export const OperatorResponseContext =
    createContext<OperatorResponseContextValue | null>(null);

export function useOperatorResponse(node_id: string | undefined) {
    const ctx = useContext(OperatorResponseContext);
    if (!ctx || !node_id) {
        return { value: undefined, setValue: () => {} } as const;
    }
    return {
        value: ctx.responses[node_id],
        setValue: (v: unknown) => ctx.setResponse(node_id, v),
    } as const;
}
