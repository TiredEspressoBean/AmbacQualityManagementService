import { useState } from "react";
import { useEditor, EditorContent, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { generateHTML } from "@tiptap/html";
import {
    ResizableHandle,
    ResizablePanel,
    ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Bold,
    Italic,
    Strikethrough,
    Code,
    Heading1,
    Heading2,
    List,
    ListOrdered,
    Quote,
    Minus,
    Undo,
    Redo,
} from "lucide-react";

const SAMPLE_CONTENT = {
    type: "doc",
    content: [
        {
            type: "heading",
            attrs: { level: 2 },
            content: [{ type: "text", text: "Substep 2: Set OD Offsets" }],
        },
        {
            type: "paragraph",
            content: [
                { type: "text", text: "Adjust the X and Z offsets per the " },
                {
                    type: "text",
                    text: "setup sheet",
                    marks: [{ type: "bold" }],
                },
                { type: "text", text: " before running the first piece." },
            ],
        },
        {
            type: "heading",
            attrs: { level: 3 },
            content: [{ type: "text", text: "Tools required" }],
        },
        {
            type: "bulletList",
            content: [
                {
                    type: "listItem",
                    content: [
                        {
                            type: "paragraph",
                            content: [{ type: "text", text: "Digital micrometer (0–1 in)" }],
                        },
                    ],
                },
                {
                    type: "listItem",
                    content: [
                        {
                            type: "paragraph",
                            content: [{ type: "text", text: "Setup sheet for P/N 11782-3" }],
                        },
                    ],
                },
                {
                    type: "listItem",
                    content: [
                        {
                            type: "paragraph",
                            content: [{ type: "text", text: "Hex key (3 mm)" }],
                        },
                    ],
                },
            ],
        },
        {
            type: "paragraph",
            content: [
                {
                    type: "text",
                    text: "Critical dimension: ",
                },
                {
                    type: "text",
                    text: "OD 1.247 ± 0.002 in",
                    marks: [{ type: "code" }],
                },
                { type: "text", text: "." },
            ],
        },
    ],
};

function Toolbar({ editor }: { editor: Editor | null }) {
    if (!editor) return null;

    const btn = (
        active: boolean,
        onClick: () => void,
        icon: React.ReactNode,
        label: string,
    ) => (
        <Button
            size="sm"
            variant={active ? "default" : "outline"}
            onClick={onClick}
            aria-label={label}
            className="h-8 w-8 p-0"
        >
            {icon}
        </Button>
    );

    return (
        <div className="flex flex-wrap items-center gap-1 border-b bg-muted/30 p-2">
            {btn(
                editor.isActive("bold"),
                () => editor.chain().focus().toggleBold().run(),
                <Bold className="h-4 w-4" />,
                "Bold",
            )}
            {btn(
                editor.isActive("italic"),
                () => editor.chain().focus().toggleItalic().run(),
                <Italic className="h-4 w-4" />,
                "Italic",
            )}
            {btn(
                editor.isActive("strike"),
                () => editor.chain().focus().toggleStrike().run(),
                <Strikethrough className="h-4 w-4" />,
                "Strikethrough",
            )}
            {btn(
                editor.isActive("code"),
                () => editor.chain().focus().toggleCode().run(),
                <Code className="h-4 w-4" />,
                "Inline code",
            )}
            <div className="mx-1 h-6 w-px bg-border" />
            {btn(
                editor.isActive("heading", { level: 1 }),
                () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
                <Heading1 className="h-4 w-4" />,
                "Heading 1",
            )}
            {btn(
                editor.isActive("heading", { level: 2 }),
                () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
                <Heading2 className="h-4 w-4" />,
                "Heading 2",
            )}
            <div className="mx-1 h-6 w-px bg-border" />
            {btn(
                editor.isActive("bulletList"),
                () => editor.chain().focus().toggleBulletList().run(),
                <List className="h-4 w-4" />,
                "Bullet list",
            )}
            {btn(
                editor.isActive("orderedList"),
                () => editor.chain().focus().toggleOrderedList().run(),
                <ListOrdered className="h-4 w-4" />,
                "Ordered list",
            )}
            {btn(
                editor.isActive("blockquote"),
                () => editor.chain().focus().toggleBlockquote().run(),
                <Quote className="h-4 w-4" />,
                "Blockquote",
            )}
            {btn(
                false,
                () => editor.chain().focus().setHorizontalRule().run(),
                <Minus className="h-4 w-4" />,
                "Horizontal rule",
            )}
            <div className="mx-1 h-6 w-px bg-border" />
            {btn(
                false,
                () => editor.chain().focus().undo().run(),
                <Undo className="h-4 w-4" />,
                "Undo",
            )}
            {btn(
                false,
                () => editor.chain().focus().redo().run(),
                <Redo className="h-4 w-4" />,
                "Redo",
            )}
        </div>
    );
}

export function DwiSpikePage() {
    const [, forceRerender] = useState(0);

    const editor = useEditor({
        extensions: [StarterKit],
        content: SAMPLE_CONTENT,
        onUpdate: () => forceRerender((n) => n + 1),
        onSelectionUpdate: () => forceRerender((n) => n + 1),
    });

    const json = editor?.getJSON() ?? SAMPLE_CONTENT;
    const html = editor
        ? generateHTML(json, [StarterKit])
        : "";

    return (
        <div className="flex h-[calc(100vh-4rem)] flex-col">
            <div className="border-b bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                <strong>/dwi-spike</strong> — throwaway exploration of TipTap as the
                Digital Work Instructions editor. Not wired to any backend.
            </div>

            <ResizablePanelGroup direction="horizontal" className="flex-1">
                <ResizablePanel defaultSize={50} minSize={30}>
                    <div className="flex h-full flex-col">
                        <div className="border-b px-4 py-2">
                            <h2 className="text-sm font-medium text-muted-foreground">
                                Edit mode (engineer authoring)
                            </h2>
                        </div>
                        <Toolbar editor={editor} />
                        <div className="flex-1 overflow-auto">
                            <EditorContent
                                editor={editor}
                                className="prose prose-sm max-w-none p-4 focus:outline-none [&_.ProseMirror]:min-h-full [&_.ProseMirror]:outline-none"
                            />
                        </div>
                    </div>
                </ResizablePanel>

                <ResizableHandle withHandle />

                <ResizablePanel defaultSize={50} minSize={30}>
                    <div className="flex h-full flex-col">
                        <div className="border-b px-4 py-2">
                            <h2 className="text-sm font-medium text-muted-foreground">
                                Rendered HTML (via generateHTML)
                            </h2>
                        </div>
                        <div className="flex-1 overflow-auto p-4">
                            <div
                                className="prose prose-sm max-w-none"
                                dangerouslySetInnerHTML={{ __html: html }}
                            />
                        </div>
                    </div>
                </ResizablePanel>
            </ResizablePanelGroup>

            <Card className="m-4 rounded-md">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                        Document JSON (editor.getJSON())
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs">
                        {JSON.stringify(json, null, 2)}
                    </pre>
                </CardContent>
            </Card>
        </div>
    );
}

export default DwiSpikePage;