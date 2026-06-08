import { Node, mergeAttributes } from "@tiptap/core";
import { ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import { Camera } from "lucide-react";
import { FileLikeCaptureView } from "../shared/FileLikeCapture";

function View(props: NodeViewProps) {
    return (
        <FileLikeCaptureView
            {...props}
            icon={<Camera className="h-4 w-4 text-muted-foreground" />}
            typeLabel="Image"
            accept="image/*"
            mockPlaceholder="Operator taps to capture or upload"
        />
    );
}

export const PhotoCapture = Node.create({
    name: "photoCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="photo-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "photo-capture" }),
            `[PHOTO] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_PHOTO = {
    type: "photoCapture",
    attrs: { node_id: "seed-photo-1", label: "Photograph the setup sheet position", required: false },
};
