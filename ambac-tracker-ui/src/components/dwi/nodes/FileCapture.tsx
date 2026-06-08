import { Node, mergeAttributes } from "@tiptap/core";
import { ReactNodeViewRenderer, type NodeViewProps } from "@tiptap/react";
import { Paperclip } from "lucide-react";
import { FileLikeCaptureView } from "../shared/FileLikeCapture";

function View(props: NodeViewProps) {
    return (
        <FileLikeCaptureView
            {...props}
            icon={<Paperclip className="h-4 w-4 text-muted-foreground" />}
            typeLabel="Any file"
            accept="*"
            mockPlaceholder="Operator drops any file (video, PDF, image, …)"
        />
    );
}

export const FileCapture = Node.create({
    name: "fileCapture",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return { node_id: { default: "" }, label: { default: "" }, required: { default: false } };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="file-capture"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "file-capture" }),
            `[FILE] ${HTMLAttributes.label || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_FILE = {
    type: "fileCapture",
    attrs: { node_id: "seed-file-1", label: "Drop any file (PDF, image, video, …)", required: false },
};
