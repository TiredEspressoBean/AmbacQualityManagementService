/**
 * Authoring affordance wrapper. The properties panel owns the edit form
 * — clicking a card creates a Tiptap NodeSelection which surfaces the
 * matching form in `NodePropertiesPanel`. This wrapper just rounds the
 * card and adds a hover ring so engineers see it's interactive.
 *
 * Operator mode (`isEditable=false`) renders the card unchanged.
 *
 * The `nodeId` prop stamps a `data-node-id` attribute on the wrapper
 * div regardless of mode. Operator-runtime missing-field handling uses
 * it to scroll-to + pulse the first incomplete capture when the
 * operator taps Confirm with required fields unfilled.
 *
 * Earlier iterations held a popover surface; that surface still lives
 * in git history if we ever want it back.
 */
export function AuthoringPopover({
    isEditable,
    nodeId,
    children,
}: {
    isEditable: boolean;
    nodeId?: string;
    children: React.ReactNode;
}) {
    if (!isEditable) {
        // Wrap in a marker div so operator-mode can find the node by id.
        return <div data-node-id={nodeId}>{children}</div>;
    }
    return (
        <div
            data-node-id={nodeId}
            className="cursor-pointer rounded-md outline-none transition hover:ring-2 hover:ring-primary/40"
        >
            {children}
        </div>
    );
}
