/**
 * AttestationCheckpoint — checkbox confirmation OR inline signature gate.
 * In operator mode the capture is recorded against the substep's response store.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { CheckSquare, PenLine } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
import {
    isSignaturePayload,
    type SignaturePayload,
} from "../shared/signature";
import { useAuthUser } from "@/hooks/useAuthUser";

type Kind = "confirm" | "signature";
type Attrs = {
    node_id: string;
    label: string;
    kind: Kind;
    prompt: string;
    required: boolean;
};

export function AttestationCheckpointEditForm({ node, updateAttributes }: NodeViewProps) {
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
                        <SelectItem value="confirm">Checkbox confirm</SelectItem>
                        <SelectItem value="signature">Signature</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            {a.kind === "confirm" && (
                <TextAttrRow attrName="prompt" label="Prompt" initial={a.prompt} update={update} />
            )}
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
    const kind = (a.kind ?? "confirm") as Kind;
    const required = a.required !== false;
    const Icon = kind === "signature" ? PenLine : CheckSquare;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const { data: me } = useAuthUser();

    const signedPayload: SignaturePayload | null =
        kind === "signature" && isSignaturePayload(value) ? value : null;

    const sign = () => {
        if (!isOperator || !me) return;
        const payload: SignaturePayload = {
            user_id: Number((me as { id: number | string }).id),
            username:
                (me as { username?: string }).username ??
                `user-${(me as { id: number | string }).id}`,
            signed_at: new Date().toISOString(),
            // data_uri reserved for SignatureCanvas integration.
        };
        setValue(payload);
    };

    const card = (
        <NodeCard
            icon={<Icon className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Attestation"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px] capitalize">{kind}</Badge>
                    {required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && value && (
                        <Badge variant="default" className="text-[10px]">Captured ✓</Badge>
                    )}
                </>
            }
        >
            {kind === "confirm" ? (
                <label className="flex items-center gap-2 text-sm" contentEditable={false}>
                    <input
                        type="checkbox"
                        disabled={!isOperator}
                        checked={isOperator ? Boolean(value) : false}
                        onChange={(e) => isOperator && setValue(e.target.checked)}
                        className={isOperator ? "" : "cursor-not-allowed"}
                    />
                    <span className={isOperator ? "" : "text-muted-foreground"}>
                        {a.prompt || "Operator confirms"}
                    </span>
                </label>
            ) : (
                <div contentEditable={false}>
                    {isOperator ? (
                        signedPayload ? (
                            <div className="rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                                <div className="font-medium">
                                    Signed by {signedPayload.username}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                    {new Date(signedPayload.signed_at).toLocaleString()}
                                </div>
                            </div>
                        ) : (
                            <button
                                type="button"
                                onClick={sign}
                                disabled={!me}
                                className="w-full rounded border border-dashed py-3 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
                            >
                                {me ? "Click to sign" : "Sign in to enable signature"}
                            </button>
                        )
                    ) : (
                        <div className="flex h-16 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                            Signature shown to operator
                        </div>
                    )}
                </div>
            )}
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

export const AttestationCheckpoint = Node.create({
    name: "attestationCheckpoint",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "" },
            kind: { default: "confirm" },
            prompt: { default: "" },
            required: { default: true },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="attestation-checkpoint"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "attestation-checkpoint" }),
            `[${HTMLAttributes.kind?.toUpperCase() || "CONFIRM"}] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_ATTESTATION_CONFIRM = {
    type: "attestationCheckpoint",
    attrs: {
        node_id: "seed-att-confirm-1",
        label: "Verify material cert",
        kind: "confirm",
        prompt: "I have checked the cert against the lot stamp.",
        required: true,
    },
};

export const SAMPLE_ATTESTATION_SIGNATURE = {
    type: "attestationCheckpoint",
    attrs: {
        node_id: "seed-att-sig-1",
        label: "Operator sign-off",
        kind: "signature",
        required: true,
    },
};
