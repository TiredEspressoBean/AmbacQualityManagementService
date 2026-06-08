/**
 * Callout — caution / note / reminder / safety content block. The variant
 * picker is rendered inline (no gear popover) since it's the only attribute
 * and inline-editing the body uses TipTap's `NodeViewContent`.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewContent,
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import {
    CALLOUT_CONFIG,
    type CalloutVariant,
} from "../shared/callout-config";

function View({ node, updateAttributes, editor }: NodeViewProps) {
    const variant = (node.attrs.variant ?? "note") as CalloutVariant;
    const cfg = CALLOUT_CONFIG[variant];
    const Icon = cfg.icon;
    const isEditable = editor.isEditable;
    return (
        <NodeViewWrapper className="my-3 not-prose">
            <div className={`rounded-md border-2 p-3 ${cfg.cls}`}>
                <div className="mb-1 flex items-center gap-2" contentEditable={false}>
                    <Icon className="h-4 w-4" />
                    {isEditable ? (
                        <select
                            value={variant}
                            onChange={(e) => updateAttributes({ variant: e.target.value })}
                            className="rounded bg-transparent text-sm font-semibold focus:outline-none"
                            aria-label="Callout variant"
                        >
                            {(Object.keys(CALLOUT_CONFIG) as CalloutVariant[]).map((v) => (
                                <option key={v} value={v} className="bg-background text-foreground">
                                    {CALLOUT_CONFIG[v].label}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <span className="text-sm font-semibold">{cfg.label}</span>
                    )}
                </div>
                <NodeViewContent className="text-sm [&_p]:my-1" />
            </div>
        </NodeViewWrapper>
    );
}

export const Callout = Node.create({
    name: "callout",
    group: "block",
    content: "paragraph+",
    defining: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { variant: { default: "note" } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="callout"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, {
                "data-type": "callout",
                "data-variant": HTMLAttributes.variant || "note",
                class: "my-3 rounded-md border-2 p-3",
            }),
            0,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_CALLOUT_CAUTION = {
    type: "callout",
    attrs: { variant: "caution" },
    content: [
        {
            type: "paragraph",
            content: [
                {
                    type: "text",
                    text: "Bar stock must be clamped firmly. Loose stock can throw at high spindle speed.",
                },
            ],
        },
    ],
};

export const SAMPLE_CALLOUT_NOTE = {
    type: "callout",
    attrs: { variant: "note" },
    content: [
        {
            type: "paragraph",
            content: [
                { type: "text", text: "The setup sheet lives in the binder above the machine." },
            ],
        },
    ],
};
