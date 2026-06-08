/**
 * InspectionSignatures — captures the DETECTED_BY and (optional) VERIFIED_BY
 * signatures on the inspection event. Maps to two `QualityReportPersonnel`
 * rows with `signed_at` set and the matching role.
 *
 * Distinct from `PersonnelRolesField` because signatures are a deliberate
 * "I attest" gesture rather than a declarative "these people were
 * involved." UX: one button per signature; clicking captures the current
 * user + timestamp. Real signature canvas (Base64 PNG payload) is deferred —
 * we capture only user+timestamp here, which is sufficient for non-regulated
 * industries. Hook points are wired so a canvas widget can drop in later.
 */
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { PenLine, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { useAuthUser } from "@/hooks/useAuthUser";
import type { SignaturePayload } from "../shared/signature";

type Attrs = {
    node_id: string;
    label: string;
    require_detected: boolean;
    require_verified: boolean;
};

type Response = {
    detected?: SignaturePayload;
    verified?: SignaturePayload;
};

export function InspectionSignaturesEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
            <div className="flex items-center justify-between border-t pt-2">
                <Label className="text-xs">Require &quot;Detected by&quot;</Label>
                <Switch
                    checked={a.require_detected}
                    onCheckedChange={(v) => updateAttributes({ require_detected: v })}
                />
            </div>
            <div className="flex items-center justify-between">
                <Label className="text-xs">Require &quot;Verified by&quot;</Label>
                <Switch
                    checked={a.require_verified}
                    onCheckedChange={(v) => updateAttributes({ require_verified: v })}
                />
            </div>
        </div>
    );
}

function SignatureSlot({
    label,
    sig,
    onSign,
    disabled,
}: {
    label: string;
    sig: SignaturePayload | undefined;
    onSign: () => void;
    disabled: boolean;
}) {
    if (sig) {
        return (
            <div className="flex items-center gap-2 rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <div className="flex flex-col">
                    <span className="font-medium">{label}: {sig.username}</span>
                    <span className="text-[10px] text-muted-foreground">
                        Signed {new Date(sig.signed_at).toLocaleString()}
                    </span>
                </div>
            </div>
        );
    }
    return (
        <button
            type="button"
            onClick={onSign}
            disabled={disabled}
            className="w-full rounded border border-dashed py-3 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50"
        >
            {disabled ? `${label} signature shown to operator` : `Sign as ${label.toLowerCase()}`}
        </button>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const current = (value as Response | undefined) ?? {};

    const { data: me } = useAuthUser();
    const sign = (which: "detected" | "verified") => {
        if (!isOperator || !me) return;
        const next: Response = {
            ...current,
            [which]: {
                // `id` from AuthUser may be a string/number depending on backend
                // serializer; cast through Number for the captured payload.
                user_id: Number((me as { id: number | string }).id),
                username: (me as { username?: string }).username ?? `user-${(me as { id: number | string }).id}`,
                signed_at: new Date().toISOString(),
            },
        };
        setValue(next);
    };

    const card = (
        <NodeCard
            icon={<PenLine className="h-4 w-4 text-muted-foreground" />}
            label={a.label || "Inspection signatures"}
            badges={
                <>
                    {a.require_detected && <Badge variant="secondary" className="text-[10px]">Detected required</Badge>}
                    {a.require_verified && <Badge variant="secondary" className="text-[10px]">Verified required</Badge>}
                    {isOperator && current.detected && current.verified && (
                        <Badge variant="default" className="text-[10px]">Both signed</Badge>
                    )}
                </>
            }
        >
            <div className="space-y-2" contentEditable={false}>
                <SignatureSlot
                    label="Detected by"
                    sig={current.detected}
                    onSign={() => sign("detected")}
                    disabled={!isOperator}
                />
                {a.require_verified && (
                    <SignatureSlot
                        label="Verified by"
                        sig={current.verified}
                        onSign={() => sign("verified")}
                        disabled={!isOperator}
                    />
                )}
            </div>
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable} nodeId={a.node_id}>{card}</AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const InspectionSignatures = Node.create({
    name: "inspectionSignatures",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            node_id: { default: "" },
            label: { default: "Inspection signatures" },
            require_detected: { default: true },
            require_verified: { default: false },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="inspection-signatures"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "inspection-signatures" }),
            `[SIGN] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_INSPECTION_SIGNATURES = {
    type: "inspectionSignatures",
    attrs: {
        node_id: "seed-inspection-signatures-1",
        label: "Inspection sign-off",
        require_detected: true,
        require_verified: false,
    },
};
