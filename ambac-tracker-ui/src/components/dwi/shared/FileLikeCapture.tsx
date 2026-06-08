import type React from "react";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    NodeViewWrapper,
    type NodeViewProps,
} from "@tiptap/react";
import { NodeCard } from "./NodeCard";
import { AuthoringPopover } from "./AuthoringPopover";
import { useDebouncedAttrs } from "./useDebouncedAttrs";
import { TextAttrRow } from "./AttrInputs";
import { useOperatorResponse } from "./OperatorResponseContext";
import { useDocumentUpload } from "@/hooks/useDocumentUpload";

type Attrs = { node_id: string; label: string; required: boolean };

export function FileLikeEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as Attrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    return (
        <div className="space-y-3">
            <TextAttrRow attrName="label" label="Label" initial={a.label} update={update} />
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

/** Shared view for PhotoCapture / FileCapture — same interaction model
 * (file picker → operator-side store), only icon / accept / placeholder
 * differ. */
export function FileLikeCaptureView(
    props: NodeViewProps & {
        icon: React.ReactNode;
        typeLabel: string;
        accept: string;
        mockPlaceholder: string;
    },
) {
    const { node, editor, icon, typeLabel, accept, mockPlaceholder } = props;
    const a = node.attrs as Attrs;
    const isOperator = !editor.isEditable;
    const { value, setValue } = useOperatorResponse(a.node_id);
    const upload = useDocumentUpload();

    // Response can be a legacy string (pre-upload) or an object once the
    // file has landed on `/api/Documents/`.
    const responseObj =
        value && typeof value === "object"
            ? (value as { document_id?: string; file_name?: string; file_url?: string })
            : null;
    const fileName = responseObj?.file_name ?? (typeof value === "string" ? value : "");
    const documentId = responseObj?.document_id;
    const fileUrl = responseObj?.file_url;

    const handleFile = async (file: File) => {
        // Optimistic: show the filename immediately so the operator gets
        // feedback before the upload resolves.
        setValue({ file_name: file.name });
        try {
            const result = await upload.mutateAsync({ file });
            setValue({
                document_id: result.document_id,
                file_name: result.file_name,
                file_url: result.file_url,
            });
        } catch {
            // Roll back to empty so the operator can retry.
            setValue("");
        }
    };

    const card = (
        <NodeCard
            icon={icon}
            label={a.label || `${typeLabel} capture`}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px]">{typeLabel}</Badge>
                    {a.required && <Badge variant="secondary" className="text-[10px]">Required</Badge>}
                    {isOperator && upload.isPending && (
                        <Badge variant="outline" className="text-[10px]">Uploading…</Badge>
                    )}
                    {isOperator && documentId && (
                        <Badge variant="default" className="text-[10px]">Uploaded ✓</Badge>
                    )}
                </>
            }
        >
            <div contentEditable={false}>
                {isOperator ? (
                    fileName ? (
                        <div className="space-y-2 rounded border border-green-500/40 bg-green-50/40 p-2 text-xs dark:bg-green-950/20">
                            {/* Inline thumbnail for images so the operator
                                sees what they captured. Other file types
                                show the filename only. */}
                            {typeLabel.toLowerCase() === "image" && fileUrl && (
                                <img
                                    src={fileUrl}
                                    alt={fileName}
                                    draggable={false}
                                    className="block max-h-48 w-full rounded border bg-muted object-contain"
                                />
                            )}
                            <div className="flex items-center gap-2">
                                <span className="font-mono">{fileName}</span>
                                {upload.isPending && (
                                    <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                                )}
                                {fileUrl && (
                                    <a
                                        href={fileUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-primary hover:underline"
                                    >
                                        View
                                    </a>
                                )}
                                <button
                                    type="button"
                                    onClick={() => setValue("")}
                                    disabled={upload.isPending}
                                    className="ml-auto text-muted-foreground hover:underline disabled:opacity-50"
                                >
                                    Clear
                                </button>
                            </div>
                        </div>
                    ) : (
                        <label className="block cursor-pointer rounded border border-dashed py-3 text-center text-xs text-muted-foreground hover:bg-muted">
                            <input
                                type="file"
                                accept={accept}
                                className="hidden"
                                onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) void handleFile(f);
                                }}
                            />
                            Tap to {typeLabel.toLowerCase() === "image" ? "capture or upload" : "upload"}
                        </label>
                    )
                ) : (
                    <div className="flex h-16 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
                        {mockPlaceholder}
                    </div>
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
