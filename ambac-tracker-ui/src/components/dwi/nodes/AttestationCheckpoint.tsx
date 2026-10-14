/**
 * AttestationCheckpoint — checkbox confirmation OR inline signature gate.
 * In operator mode the capture is recorded against the substep's response store.
 */
import { useState } from "react";
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
import { usePartContext } from "../shared/PartContext";
import { useSignaturePrompt, type SignatureRetry } from "@/components/dwi/useSignaturePrompt";
import { useGateSignatures, useSignGate, useClearGateSignature } from "@/hooks/useGateSignature";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { toast } from "sonner";
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
                <Label className="text-xs">How it's signed</Label>
                <Select
                    value={a.kind}
                    onValueChange={(v) => updateAttributes({ kind: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="confirm">Check off — a tick, under their login</SelectItem>
                        <SelectItem value="signature">Signature + password — they draw and re-enter their own password</SelectItem>
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
    const ctx = usePartContext();

    // A signature block is signed where it sits, before the substep is submitted:
    // the operator draws and re-enters their own password, and the server records it
    // against (execution, substep, node) with this block's label as the meaning. It
    // used to be one unauthenticated click setting a client-side payload, while the
    // catalog entry advertised "Require a signature".
    const scope = {
        stepExecutionId: ctx.step_execution_id ? String(ctx.step_execution_id) : null,
        batchExecutionId: ctx.batch_execution_id ? String(ctx.batch_execution_id) : null,
        substepId: ctx.substep_id ? String(ctx.substep_id) : null,
    };
    const canSign = !!scope.substepId && !!(scope.stepExecutionId || scope.batchExecutionId);
    const { data: gates } = useGateSignatures(scope);
    const signGate = useSignGate(scope);
    const clearGate = useClearGateSignature(scope);
    const signed = (gates ?? []).find((g) => g.node_id === String(a.node_id)) ?? null;
    const { request, dialog } = useSignaturePrompt();

    // In the editor there is no part and no execution, so a signature has nowhere
    // to go. The controls still work, locally, so the author can see exactly what
    // the operator will face — including the password dialog — and can clear it
    // again. Nothing here is written anywhere.
    const [previewConfirmed, setPreviewConfirmed] = useState(false);
    const [previewSignedAt, setPreviewSignedAt] = useState<string | null>(null);

    // What the card shows, from whichever source applies: the recorded signature on
    // the floor, or the author's local preview in the editor.
    const signedView = isOperator
        ? (signed && {
            by: signed.completed_by_name ?? "you",
            at: signed.completed_at ?? null,
            verified: signed.verification_method === "PASSWORD",
        })
        : (previewSignedAt && {
            by: me?.username ?? "you",
            at: previewSignedAt,
            verified: true,
        });

    const signPreview = async () => {
        const got = await request(a.label || "Sign-off");
        if (!got) return;
        setPreviewSignedAt(new Date().toISOString());
    };

    const sign = async () => {
        if (!isOperator) return signPreview();
        if (!me || !canSign) return;
        const meaning = a.label || "Sign-off";
        let retry: SignatureRetry | undefined;
        for (;;) {
            const got = await request(meaning, retry);
            if (!got) return; // cancelled — nothing is recorded
            try {
                await signGate.mutateAsync({
                    nodeId: String(a.node_id),
                    signature_data: got.signature_data,
                    password: got.password,
                });
                return;
            } catch (e) {
                const msg = apiErrorMessage(e) ?? "";
                // A wrong password re-opens the prompt with the drawing kept and only
                // the password cleared. Anything else (already submitted, already
                // signed) is final — re-asking would just fail again.
                if (!/password/i.test(msg)) {
                    toast.error("Could not sign", { description: msg || undefined });
                    return;
                }
                retry = { signature_data: got.signature_data, reason: msg };
            }
        }
    };

    const card = (
        <NodeCard
            icon={<Icon className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Attestation"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">
                        {kind === "signature" ? "Signature + password" : "Check off"}
                    </Badge>
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
                        checked={isOperator ? Boolean(value) : previewConfirmed}
                        onChange={(e) =>
                            isOperator ? setValue(e.target.checked)
                                       : setPreviewConfirmed(e.target.checked)}
                    />
                    <span>{a.prompt || "Operator confirms"}</span>
                </label>
            ) : (
                <div contentEditable={false}>
                    {signedView ? (
                        <div className="rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                            <div className="font-medium">
                                Signed by {signedView.by}
                            </div>
                            <div className="text-[10px] text-muted-foreground">
                                {signedView.at ? new Date(signedView.at).toLocaleString() : null}
                                {signedView.verified ? " · password verified" : null}
                                {!isOperator ? " · preview, nothing recorded" : null}
                            </div>
                            {/* Provisional until the substep is submitted: the server
                                refuses afterwards, and refuses someone else's signature
                                unless you hold the authority to clear it. */}
                            <button
                                type="button"
                                onClick={() => {
                                    if (!isOperator) {
                                        setPreviewSignedAt(null);
                                        return;
                                    }
                                    if (!signed) return;
                                    clearGate.mutate(signed.id, {
                                        onError: (e) =>
                                            toast.error("Could not undo the signature", {
                                                description: apiErrorMessage(e) ?? undefined,
                                            }),
                                    });
                                }}
                                disabled={clearGate.isPending}
                                className="mt-1 text-[10px] underline text-muted-foreground hover:text-foreground disabled:opacity-50"
                            >
                                {clearGate.isPending ? "Undoing..." : "Undo signature"}
                            </button>
                        </div>
                    ) : (
                        <button
                            type="button"
                            onClick={sign}
                            disabled={isOperator && (!me || signGate.isPending || !canSign)}
                            className="w-full rounded border border-dashed py-3 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
                        >
                            {!isOperator
                                ? "Sign — draw and enter your password (preview)"
                                : !me
                                    ? "Sign in to enable signature"
                                    : !canSign
                                        ? "Open this substep on a part to sign"
                                        : signGate.isPending
                                            ? "Signing..."
                                            : "Sign — draw and enter your password"}
                        </button>
                    )}
                    {dialog}
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
