/**
 * DocumentLink — author-embedded reference to an existing Document. Renders
 * as a clickable card that opens / downloads the linked file. Unlike Media
 * (which inlines an image / video player), this node is intentionally a
 * *link* — used for procedures, spec sheets, drawings, and other documents
 * the operator should open in a separate viewer.
 *
 * Storage shape:
 *   { document_id: uuid, file_name: string, file_url: string, label: string }
 *
 * `document_id` is the source of truth; `file_name` and `file_url` are
 * cached at author-time so the operator-runtime renderer doesn't need a
 * round-trip to display the card. If the document is later renamed or
 * moved, the cached fields go stale — but the document_id still resolves
 * to the current document via a normal Documents lookup if the renderer
 * wants to refresh.
 */
import { useMemo, useRef, useState } from "react";
import { Node, mergeAttributes } from "@tiptap/core";
import {
    NodeViewWrapper,
    ReactNodeViewRenderer,
    type NodeViewProps,
} from "@tiptap/react";
import {
    FileText,
    ExternalLink,
    Loader2,
    Search,
    Upload,
    ClipboardList,
    Settings,
    Package,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NodeCard } from "../shared/NodeCard";
import { AuthoringPopover } from "../shared/AuthoringPopover";
import { useDebouncedAttrs } from "../shared/useDebouncedAttrs";
import { TextAttrRow } from "../shared/AttrInputs";
import { useRetrieveDocuments } from "@/hooks/useRetrieveDocuments";
import { useDocumentUpload } from "@/hooks/useDocumentUpload";
import { useQaDocuments } from "@/hooks/useQaDocuments";
import { useSubstepAuthoringContext } from "../shared/SubstepAuthoringContext";

type DocumentLinkAttrs = {
    document_id: string | null;
    file_name: string;
    file_url: string;
    label: string;
};

type ScopedDoc = {
    id: string;
    file_name: string;
    file_url: string;
    version?: number;
    source: "Work Order" | "Current Step" | "Part Type";
};

function sourceIcon(source: ScopedDoc["source"]) {
    switch (source) {
        case "Work Order":
            return <ClipboardList className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />;
        case "Current Step":
            return <Settings className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />;
        case "Part Type":
            return <Package className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />;
    }
}

export function DocumentLinkEditForm({ node, updateAttributes }: NodeViewProps) {
    const a = node.attrs as DocumentLinkAttrs;
    const update = useDebouncedAttrs(updateAttributes, 250);
    const [search, setSearch] = useState("");
    const upload = useDocumentUpload();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { workOrderId } = useSubstepAuthoringContext();

    // Scoped: WorkOrder's qa_documents (work order + current step + part type).
    // Mirrors the operator-runtime Documents & References panel.
    const qa = useQaDocuments(workOrderId ?? "");

    // Unscoped fallback: global text search. Only used when no workOrderId is
    // in context (the authoring page on its own doesn't have one).
    const trimmed = search.trim();
    const fallback = useRetrieveDocuments(
        !workOrderId && trimmed.length > 1 ? ({ search: trimmed, page_size: 10 } as never) : undefined,
        undefined,
        { enabled: !workOrderId && trimmed.length > 1 } as never,
    );

    const scopedResults = useMemo<ScopedDoc[]>(() => {
        if (!qa.data) return [];
        const data = qa.data as {
            work_order_documents?: Array<{ id: string; file_name: string; file_url: string; version?: number }>;
            current_step_documents?: Array<{ id: string; file_name: string; file_url: string; version?: number }>;
            part_type_documents?: Array<{ id: string; file_name: string; file_url: string; version?: number }>;
        };
        const tag = (
            arr: Array<{ id: string; file_name: string; file_url: string; version?: number }> | undefined,
            source: ScopedDoc["source"],
        ): ScopedDoc[] => (arr ?? []).map((d) => ({ ...d, source }));
        const all = [
            ...tag(data.work_order_documents, "Work Order"),
            ...tag(data.current_step_documents, "Current Step"),
            ...tag(data.part_type_documents, "Part Type"),
        ];
        // Drop dupes by id
        const seen = new Set<string>();
        const unique = all.filter((d) => {
            if (seen.has(d.id)) return false;
            seen.add(d.id);
            return true;
        });
        if (trimmed) {
            const q = trimmed.toLowerCase();
            return unique.filter((d) => d.file_name.toLowerCase().includes(q));
        }
        return unique;
    }, [qa.data, trimmed]);

    const fallbackResults = useMemo<ScopedDoc[]>(() => {
        const list = (fallback.data?.results ?? []) as Array<{
            id: string;
            file_name: string;
            file_url: string;
            version?: number;
        }>;
        return list.map((d) => ({ ...d, source: "Work Order" as const }));
    }, [fallback.data]);

    const results = workOrderId ? scopedResults : fallbackResults;
    const isFetching = workOrderId ? qa.isLoading : fallback.isFetching;

    const handlePick = (doc: ScopedDoc) => {
        updateAttributes({
            document_id: doc.id,
            file_name: doc.file_name,
            file_url: doc.file_url,
            label: a.label || doc.file_name,
        });
        setSearch("");
    };

    const handleUpload = async (file: File) => {
        try {
            const result = await upload.mutateAsync({ file });
            updateAttributes({
                document_id: result.document_id,
                file_name: result.file_name,
                file_url: result.file_url ?? "",
                label: a.label || result.file_name,
            });
        } catch {
            /* hook surfaces its own error toast */
        }
    };

    return (
        <div className="space-y-3">
            <TextAttrRow
                attrName="label"
                label="Label"
                initial={a.label}
                update={update}
            />

            <div className="space-y-1">
                <Label className="text-xs">Linked document</Label>
                {a.document_id ? (
                    <div className="flex items-center justify-between rounded border bg-muted/30 px-2 py-1.5 text-xs">
                        <span className="truncate font-mono">{a.file_name}</span>
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs text-destructive hover:bg-destructive/10"
                            onClick={() =>
                                updateAttributes({
                                    document_id: null,
                                    file_name: "",
                                    file_url: "",
                                })
                            }
                        >
                            Clear
                        </Button>
                    </div>
                ) : (
                    <p className="text-xs text-muted-foreground">
                        {workOrderId
                            ? "Pick from work-order documents below or upload a new one."
                            : "No work-order context. Search all documents or upload a new one."}
                    </p>
                )}
            </div>

            <div className="space-y-1">
                <Label className="text-xs">
                    {workOrderId ? "Work-order documents" : "Search documents"}
                </Label>
                <div className="relative">
                    <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder={
                            workOrderId
                                ? "Filter…"
                                : "Type at least 2 characters…"
                        }
                        className="h-8 pl-7 text-sm"
                    />
                </div>
                {(workOrderId || trimmed.length > 1) && (
                    <div className="max-h-48 overflow-auto rounded border bg-background">
                        {isFetching ? (
                            <div className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-muted-foreground">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Loading…
                            </div>
                        ) : results.length === 0 ? (
                            <div className="px-2 py-1.5 text-xs text-muted-foreground">
                                {workOrderId
                                    ? "No documents linked to this work order, current step, or part type."
                                    : "No matches."}
                            </div>
                        ) : (
                            <ul className="divide-y">
                                {results.map((doc) => (
                                    <li key={doc.id}>
                                        <button
                                            type="button"
                                            onClick={() => handlePick(doc)}
                                            className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs hover:bg-muted"
                                        >
                                            {sourceIcon(doc.source)}
                                            <span className="flex-1 truncate">{doc.file_name}</span>
                                            {workOrderId && (
                                                <Badge variant="outline" className="text-[10px]">
                                                    {doc.source}
                                                </Badge>
                                            )}
                                            {doc.version != null && (
                                                <Badge variant="outline" className="text-[10px]">
                                                    v{doc.version}
                                                </Badge>
                                            )}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
            </div>

            <div className="flex items-center gap-2">
                <input
                    ref={fileInputRef}
                    type="file"
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
                    Upload new
                </Button>
                <span className="text-xs text-muted-foreground">
                    or pick from the list above
                </span>
            </div>
        </div>
    );
}

function View(props: NodeViewProps) {
    const { node, editor } = props;
    const a = node.attrs as DocumentLinkAttrs;
    const { label = "", file_name = "", file_url = "", document_id } = a;
    const displayLabel = label || file_name || "Document";
    const hasTarget = Boolean(file_url || document_id);

    return (
        <NodeViewWrapper className="my-3 not-prose">
            <AuthoringPopover isEditable={editor.isEditable}>
                <NodeCard
                    icon={<FileText className="h-4 w-4 text-muted-foreground" />}
                    label={displayLabel}
                    badges={
                        file_name && file_name !== displayLabel ? (
                            <Badge variant="outline" className="text-[10px] truncate max-w-[16rem]">
                                {file_name}
                            </Badge>
                        ) : null
                    }
                    rightSlot={
                        hasTarget && file_url ? (
                            <a
                                href={file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                // contentEditable=false keeps clicks from being
                                // intercepted by the editor's selection logic.
                                contentEditable={false}
                                onMouseDown={(e) => e.stopPropagation()}
                                className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-primary hover:bg-primary/10"
                            >
                                Open <ExternalLink className="h-3 w-3" />
                            </a>
                        ) : (
                            "no link"
                        )
                    }
                />
            </AuthoringPopover>
        </NodeViewWrapper>
    );
}

export const DocumentLink = Node.create({
    name: "documentLink",
    group: "block",
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes() {
        return {
            document_id: { default: null },
            file_name: { default: "" },
            file_url: { default: "" },
            label: { default: "" },
        };
    },
    parseHTML() {
        return [{ tag: 'div[data-type="document-link"]' }];
    },
    renderHTML({ HTMLAttributes }) {
        return [
            "div",
            mergeAttributes(HTMLAttributes, { "data-type": "document-link" }),
            `[DOCUMENT] ${HTMLAttributes.label || HTMLAttributes.file_name || ""}`,
        ];
    },
    addNodeView() {
        return ReactNodeViewRenderer(View);
    },
});

export const SAMPLE_DOCUMENT_LINK = {
    type: "documentLink",
    attrs: {
        document_id: null,
        file_name: "",
        file_url: "",
        label: "Linked document",
    },
};
