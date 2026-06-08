/** ChoiceInput — radio or select picker. Engineer manages the options list
 * in the gear popover (add / remove / reorder rows). */
import { useMemo, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { ListChecks, Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";

type Kind = "radio" | "select";
type Attrs = {
    node_id: string;
    label: string;
    kind: Kind;
    options: string[];
    required: boolean;
};

function OptionsEditor({
    options,
    update,
}: {
    options: string[];
    update: (next: string[]) => void;
}) {
    const [draft, setDraft] = useState("");
    return (
        <div className="space-y-1">
            <Label className="text-xs">Options</Label>
            <div className="space-y-1">
                {options.map((opt, i) => (
                    <div key={i} className="flex items-center gap-1">
                        <Input
                            value={opt}
                            onChange={(e) => {
                                const next = options.slice();
                                next[i] = e.target.value;
                                update(next);
                            }}
                            className="h-7 text-xs"
                        />
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => update(options.filter((_, j) => j !== i))}
                            className="h-7 w-7 p-0"
                        >
                            <X className="h-3 w-3" />
                        </Button>
                    </div>
                ))}
            </div>
            <div className="flex items-center gap-1 pt-1">
                <Input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="Add option…"
                    className="h-7 text-xs"
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && draft.trim()) {
                            e.preventDefault();
                            update([...options, draft.trim()]);
                            setDraft("");
                        }
                    }}
                />
                <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={!draft.trim()}
                    onClick={() => {
                        update([...options, draft.trim()]);
                        setDraft("");
                    }}
                    className="h-7 w-7 p-0"
                >
                    <Plus className="h-3 w-3" />
                </Button>
            </div>
        </div>
    );
}

export function ChoiceInputEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <div className="space-y-1">
                <Label className="text-xs">Kind</Label>
                <Select
                    value={a.kind}
                    onValueChange={(v) => updateAttributes({ kind: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="radio">Radio buttons</SelectItem>
                        <SelectItem value="select">Dropdown select</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <OptionsEditor
                options={Array.isArray(a.options) ? a.options : []}
                update={(next) => updateAttributes({ options: next })}
            />
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Required</Label>
                <Switch
                    checked={a.required}
                    onCheckedChange={(checked) => updateAttributes({ required: checked })}
                />
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const kind = (a.kind ?? "radio") as Kind;
    const options: string[] = Array.isArray(a.options) ? a.options : [];
    const required = a.required === true;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const v = typeof value === "string" ? value : "";

    const groupName = useMemo(
        () => `choice-${a.node_id || Math.random().toString(36).slice(2)}`,
        [a.node_id],
    );

    const card = (
        <NodeCard
            icon={<ListChecks className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Choice"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && v && (
                        <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                    )}
                </>
            }
        >
            <div contentEditable={false}>
                {options.length === 0 && (
                    <div className="text-xs italic text-muted-foreground">
                        No options — open the gear menu to add some.
                    </div>
                )}
                {kind === "radio" ? (
                    <div className="space-y-1">
                        {options.map((opt) => (
                            <label
                                key={opt}
                                className={`flex items-center gap-2 text-sm ${
                                    isOperator ? "" : "text-muted-foreground"
                                }`}
                            >
                                <input
                                    type="radio"
                                    name={groupName}
                                    disabled={!isOperator}
                                    checked={isOperator ? v === opt : false}
                                    onChange={() => isOperator && setValue(opt)}
                                />
                                {opt}
                            </label>
                        ))}
                    </div>
                ) : (
                    <select
                        disabled={!isOperator}
                        value={v}
                        onChange={(e) => isOperator && setValue(e.target.value)}
                        className="rounded border bg-background px-2 py-1 text-sm"
                    >
                        <option value="">— select —</option>
                        {options.map((opt) => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>
                {card}
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const ChoiceInput = Node.create({
    name: "choiceInput",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "radio" },
            options: { default: [] },
            required: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="choice-input"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        const options = Array.isArray(HTMLAttributes.options)
            ? HTMLAttributes.options.join(" / ")
            : "";
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "choice-input" }),
            `${HTMLAttributes.label || "Choice"}: ${options}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_CHOICE_RADIO = {
    type: "choiceInput",
    attrs: {
        node_id: "seed-choice-radio-1",
        label: "Bar stock condition",
        kind: "radio",
        options: ["Clean", "Light surface scale", "Heavy scale — requires extra pass"],
        required: true,
    },
};

export const SAMPLE_CHOICE_SELECT = {
    type: "choiceInput",
    attrs: {
        node_id: "seed-choice-select-1",
        label: "Cutting tool",
        kind: "select",
        options: ["CCMT-32.51 (general)", "VBMT-110304 (finish)", "DCMT-070204 (light)"],
        required: false,
    },
};
