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
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useState } from "react";
import { TextAttrRow } from "../shared/AttrInputs";
import { useSignaturePrompt } from "@/components/dwi/useSignaturePrompt";
import { SecondPersonCosignDialog } from "@/components/second-person-cosign-dialog";
import { useOperatorResponse } from "../shared/OperatorResponseContext";
import { useAuthUser } from "@/hooks/useAuthUser";
import type { SignaturePayload } from "../shared/signature";

type Attrs = {
    node_id: string;
    label: string;
    require_detected: boolean;
    require_verified: boolean;
    /** How the finder signs: a click under their login, or their own drawn
     *  signature and password. The verifier is always a second person. */
    detected_assurance: "confirm" | "signature";
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
            <div className="space-y-1 pl-2">
                <Label className="text-xs">How &quot;Detected by&quot; signs</Label>
                <Select
                    value={a.detected_assurance ?? "confirm"}
                    onValueChange={(v) => updateAttributes({ detected_assurance: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="confirm">Check off — a click, under their login</SelectItem>
                        <SelectItem value="signature">Signature + password — they draw and re-enter their own password</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="flex items-center justify-between">
                <Label className="text-xs">Require &quot;Verified by&quot;</Label>
                <Switch
                    checked={a.require_verified}
                    onCheckedChange={(v) => updateAttributes({ require_verified: v })}
                />
            </div>
            <p className="text-[10px] text-muted-foreground">
                The verifier is always a second person: they enter their own email and
                password at the operator&apos;s terminal. It can never be whoever did the
                work.
            </p>
        </div>
    );
}

function SignatureSlot({
    label,
    sig,
    onSign,
    disabled,
    preview = false,
    onClear,
}: {
    label: string;
    sig: SignaturePayload | undefined;
    onSign: () => void;
    disabled: boolean;
    preview?: boolean;
    onClear?: () => void;
}) {
    if (sig) {
        return (
            <div className="flex items-center gap-2 rounded border border-green-500/40 bg-green-50/40 dark:bg-green-950/20 p-2 text-xs">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <div className="flex flex-col">
                    <span className="font-medium">{label}: {sig.username}</span>
                    <span className="text-[10px] text-muted-foreground">
                        Signed {new Date(sig.signed_at).toLocaleString()}
                        {preview ? " · preview, nothing recorded" : null}
                    </span>
                </div>
                {onClear && (
                    <button
                        type="button"
                        onClick={onClear}
                        className="ml-auto text-[10px] underline text-muted-foreground hover:text-foreground"
                    >
                        {preview ? "Clear" : "Undo"}
                    </button>
                )}
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
            {`Sign as ${label.toLowerCase()}`}{preview ? " (preview)" : ""}
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
    const { request, dialog } = useSignaturePrompt();
    const [cosignOpen, setCosignOpen] = useState(false);
    const [cosignError, setCosignError] = useState<string | null>(null);
    // In the editor there is no inspection to sign, so both slots run locally: the
    // author sees what the finder and the verifier each face, and can clear it
    // again. Nothing is recorded.
    const [preview, setPreview] = useState<Response>({});
    const shown: Response = isOperator ? current : preview;

    const detectedNeedsSignature = (a.detected_assurance ?? "confirm") === "signature";

    // The finder attests to their own work, so this is their own signature: a click,
    // or — when the author asked for it — their drawing and their password.
    // `auth/user/` returns the user as `pk`, NOT `id`; reading `.id` once recorded
    // every player-captured signature with a null signer.
    const signDetected = async () => {
        if (!isOperator) {
            if (detectedNeedsSignature && !(await request(a.label || "Detected by"))) return;
            setPreview({
                ...preview,
                detected: {
                    user_id: me?.pk ?? 0,
                    username: me?.username ?? "you",
                    signed_at: new Date().toISOString(),
                } as SignaturePayload,
            });
            return;
        }
        if (!me) return;
        const base = {
            user_id: me.pk,
            username: me.username ?? `user-${me.pk}`,
            signed_at: new Date().toISOString(),
        };
        if (!detectedNeedsSignature) {
            setValue({ ...current, detected: base as SignaturePayload });
            return;
        }
        const got = await request(a.label || "Detected by");
        if (!got) return;
        setValue({
            ...current,
            detected: {
                ...base,
                data_uri: got.signature_data,
                password: got.password,
            } as unknown as SignaturePayload,
        });
    };

    // The verifier is a second person standing at the operator's keyboard, so they
    // identify themselves rather than inheriting the session — one browser, one
    // login. The server resolves this slot from their credentials and never stamps
    // it from the session, so the operator cannot fill it.
    const confirmVerifier = (credentials: { email: string; password: string }) => {
        setCosignError(null);
        if (!isOperator) {
            setPreview({
                ...preview,
                verified: {
                    user_id: 0,
                    username: credentials.email,
                    signed_at: new Date().toISOString(),
                } as SignaturePayload,
            });
            setCosignOpen(false);
            return;
        }
        setValue({
            ...current,
            verified: {
                cosign_email: credentials.email,
                cosign_password: credentials.password,
            } as unknown as SignaturePayload,
        });
        setCosignOpen(false);
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
                    sig={shown.detected}
                    onSign={signDetected}
                    disabled={false}
                    preview={!isOperator}
                    onClear={() =>
                        isOperator
                            ? setValue({ ...current, detected: undefined })
                            : setPreview({ ...preview, detected: undefined })}
                />
                {dialog}
                <SecondPersonCosignDialog
                    open={cosignOpen}
                    onOpenChange={setCosignOpen}
                    title="Verify this inspection"
                    description="A verification is a second person's. Sign in here with your own email and password - it cannot be the person who did the work."
                    emailLabel="Verifier's email"
                    confirmationText="I confirm this is my signature and that I am verifying work I did not do."
                    error={cosignError}
                    onConfirm={confirmVerifier}
                />
                {a.require_verified && (
                    <SignatureSlot
                        label="Verified by"
                        sig={shown.verified}
                        onSign={() => { setCosignError(null); setCosignOpen(true); }}
                        disabled={false}
                        preview={!isOperator}
                        onClear={() =>
                            isOperator
                                ? setValue({ ...current, verified: undefined })
                                : setPreview({ ...preview, verified: undefined })}
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
            // How the person who found it signs. "confirm" is a click under their
            // login; "signature" makes them draw and re-enter their own password,
            // for a finding whose authorship has to be provable. The verifying
            // slot is always a second person's email and password — one terminal
            // has one session, so it could never be the signed-in user.
            detected_assurance: { default: "confirm" },
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
