/**
 * SubstepOperatorView — operator-facing render of a substep's body_blocks.
 *
 * Different from `SubstepEditor` (engineer + preview dual pane) — this is
 * a single editable=false editor wrapped in `OperatorResponseContext` so
 * the operator's captures (measurements, choices, signatures, defects,
 * annotations) land in a local response map. Persistence is the parent
 * page's job — this component just renders + collects.
 *
 * Why we don't reuse `SubstepEditor` here: the operator runtime doesn't
 * want a side-by-side authoring + preview surface; it wants a clean
 * single-column form-style experience. Same nodes, different layout.
 */
import { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import { DWI_EXTENSIONS } from "@/lib/dwi/extensions";

const PROSE_CLASSES = "prose prose-sm max-w-none dark:prose-invert";

export function SubstepOperatorView({
    body,
    className = "",
}: {
    body: object;
    className?: string;
}) {
    const editor = useEditor({
        extensions: DWI_EXTENSIONS,
        content: body,
        editable: false,
    });

    // `useEditor` initializes content once and otherwise reuses the editor
    // instance. When the operator navigates between substeps the parent
    // passes a different `body` — we have to push it into the existing
    // editor or stale captures from the previous substep stay on screen.
    useEffect(() => {
        if (!editor) return;
        editor.commands.setContent(body, { emitUpdate: false });
    }, [editor, body]);

    if (!editor) {
        return <div className={`p-4 text-sm text-muted-foreground ${className}`}>Loading…</div>;
    }

    return (
        <EditorContent
            editor={editor}
            className={`px-4 py-3 [&_.ProseMirror]:outline-none ${PROSE_CLASSES} ${className}`}
        />
    );
}
