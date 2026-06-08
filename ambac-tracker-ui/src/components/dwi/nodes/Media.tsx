/**
 * Media — author-embedded image / video / 3D-model reference. Renders a
 * real `<img>` / `<video>` from `src`; falls back to a placeholder when
 * src is empty or the load fails. Width is always 100% of the container;
 * height is author-controlled via a preset (sm / md / lg / xl / full).
 *
 * Documents-service upload integration is a follow-up — for now author
 * can paste a URL or a Documents file URL directly into `src`.
 */
import { useEffect, useRef, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import { Image as ImageIcon, AlertTriangle, Upload, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
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
import { useDocumentUpload } from "@/hooks/useDocumentUpload";

type MediaKind = "image" | "video" | "3d_model";
type MediaSize = "sm" | "md" | "lg" | "xl" | "full";

type MediaAttrs = {
    kind: MediaKind;
    src: string;
    caption: string;
    size: MediaSize;
};

const SIZE_LABELS: Record<MediaSize, string> = {
    sm: "Small (~160px)",
    md: "Medium (~280px)",
    lg: "Large (~400px)",
    xl: "Extra large (~560px)",
    full: "Native (no cap)",
};

// Max-height per preset. Width is always 100% of the container; the
// browser shrinks the image proportionally with `object-contain`.
const SIZE_MAX_HEIGHT: Record<MediaSize, string> = {
    sm: "10rem",     // ~160px
    md: "17.5rem",   // ~280px
    lg: "25rem",     // ~400px
    xl: "35rem",     // ~560px
    full: "none",
};

export function MediaEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as MediaAttrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const upload = useDocumentUpload();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const acceptByKind: Record<MediaKind, string> = {
        image: "image/*",
        video: "video/*",
        "3d_model": ".glb,.gltf,.step,.stp,.stl",
    };

    const handleUpload = async (file: File) => {
        try {
            const result = await upload.mutateAsync({ file });
            // Persist both the raw URL (for display) and the document_id
            // (for permissions / audit). Caption falls back to filename
            // when the author hasn't set one explicitly.
            const patch: Partial<MediaAttrs> & { document_id?: string } = {
                src: result.file_url ?? "",
                document_id: result.document_id,
            };
            if (!a.caption) patch.caption = result.file_name;
            updateAttributes(patch);
        } catch {
            /* upload hook surfaces its own error toast */
        }
    };

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
                        <SelectItem value="image">Image</SelectItem>
                        <SelectItem value="video">Video</SelectItem>
                        <SelectItem value="3d_model">3D model</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <TextAttrRow attrName="caption" label="Caption" initial={a.caption} update={update} />
            <TextAttrRow attrName="src" label="Source URL" initial={a.src} update={update} monospace />
            <div className="flex items-center gap-2">
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={acceptByKind[a.kind] ?? "*"}
                    className="hidden"
                    onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) void handleUpload(f);
                        e.target.value = "";
                    }}
                />
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8"
                    disabled={upload.isPending}
                    onClick={() => fileInputRef.current?.click()}
                >
                    {upload.isPending ? (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    ) : (
                        <Upload className="mr-1.5 h-3.5 w-3.5" />
                    )}
                    Upload file
                </Button>
                <span className="text-xs text-muted-foreground">
                    or paste a URL above
                </span>
            </div>
            <div className="space-y-1">
                <Label className="text-xs">Size</Label>
                <Select
                    value={a.size ?? "md"}
                    onValueChange={(v) => updateAttributes({ size: v })}
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {(Object.keys(SIZE_LABELS) as MediaSize[]).map((s) => (
                            <SelectItem key={s} value={s}>{SIZE_LABELS[s]}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
        </div>
    );
}

function MediaPreview({
    kind,
    src,
    size,
}: {
    kind: MediaKind;
    src: string;
    size: MediaSize;
}) {
    const [errored, setErrored] = useState(false);
    // Reset error state when src changes so a fixed URL can re-render.
    useEffect(() => {
        setErrored(false);
    }, [src]);

    const maxHeight = SIZE_MAX_HEIGHT[size] ?? SIZE_MAX_HEIGHT.md;
    const frameStyle: React.CSSProperties = {
        maxHeight: maxHeight === "none" ? undefined : maxHeight,
    };

    if (!src) {
        return (
            <div
                className="flex w-full items-center justify-center rounded border border-dashed bg-muted text-xs text-muted-foreground"
                style={{ height: maxHeight === "none" ? "8rem" : maxHeight }}
            >
                Paste a source URL in the properties panel to preview.
            </div>
        );
    }

    if (errored) {
        return (
            <div
                className="flex w-full flex-col items-center justify-center gap-1 rounded border border-destructive/40 bg-destructive/5 text-xs text-destructive"
                style={{ height: maxHeight === "none" ? "8rem" : maxHeight }}
            >
                <AlertTriangle className="h-4 w-4" />
                <span>Couldn’t load {kind} from src.</span>
                <span className="font-mono opacity-70 break-all px-2 text-center">{src}</span>
            </div>
        );
    }

    if (kind === "image") {
        return (
            <img
                src={src}
                alt=""
                draggable={false}
                onError={() => setErrored(true)}
                className="block w-full rounded border bg-muted object-contain"
                style={frameStyle}
            />
        );
    }
    if (kind === "video") {
        return (
            <video
                src={src}
                controls
                preload="metadata"
                onError={() => setErrored(true)}
                className="block w-full rounded border bg-muted"
                style={frameStyle}
            />
        );
    }
    // 3D model — engineers should reach for the PartAnnotation node when
    // they want the interactive viewer. Here we just show a placeholder.
    return (
        <div
            className="flex w-full items-center justify-center rounded border bg-muted text-xs text-muted-foreground"
            style={{ height: maxHeight === "none" ? "8rem" : maxHeight }}
        >
            📦 3D model — use PartAnnotation for an interactive viewer
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as MediaAttrs;
    const { kind = "image", src = "", caption = "", size = "md" } = a;

    const card = (
        <NodeCard
            icon={<ImageIcon className="h-4 w-4 text-muted-foreground" />}
            label={caption || "Media"}
            badges={
                <>
                    <Badge variant="outline" className="text-[10px] capitalize">
                        {kind.replace("_", " ")}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] uppercase">
                        {size}
                    </Badge>
                </>
            }
            rightSlot={src ? null : "no src"}
        >
            <MediaPreview kind={kind} src={src} size={size} />
        </NodeCard>
    );

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable}>
                {card}
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const Media = Node.create({
    name: "media",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            kind: { default: "image" },
            src: { default: "" },
            caption: { default: "" },
            size: { default: "md" },
            document_id: { default: null },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="media"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "media" }),
            `[${HTMLAttributes.kind?.toUpperCase() || "MEDIA"}] ${
                HTMLAttributes.caption || HTMLAttributes.src || ""
            }`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_MEDIA = {
    type: "media",
    attrs: {
        kind: "image",
        src: "",
        caption: "Setup sheet — P/N 11782-3",
        size: "md",
        document_id: null,
    },
};
