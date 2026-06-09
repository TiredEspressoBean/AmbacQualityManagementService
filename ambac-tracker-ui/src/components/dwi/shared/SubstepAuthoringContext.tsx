import { createContext, useContext, type ReactNode } from "react";

/**
 * Context for authoring-time scope information made available to TipTap
 * node edit forms. Set by SubstepEditorPage so nodes like DocumentLink
 * can scope their pickers to the surrounding step / process / part type.
 *
 * All fields are optional — the spike page (DwiSpikePage) doesn't have a
 * real step/process and should still render the editor without crashing.
 */
export type SubstepAuthoringContextValue = {
    stepId?: string;
    processId?: string;
    partTypeId?: string;
    /** Optional work-order context. When present, DocumentLink and similar
     *  pickers scope their suggestions to the work order's resolved document
     *  set (mirroring the operator-runtime "Documents & References" panel). */
    workOrderId?: string;
};

const Context = createContext<SubstepAuthoringContextValue>({});

export function SubstepAuthoringProvider({
    value,
    children,
}: {
    value: SubstepAuthoringContextValue;
    children: ReactNode;
}) {
    return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useSubstepAuthoringContext(): SubstepAuthoringContextValue {
    return useContext(Context);
}
