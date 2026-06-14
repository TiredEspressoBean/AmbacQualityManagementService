/**
 * `/` slash command for the DWI editor — a dependency-free alternative to
 * @tiptap/suggestion (not installed). A small ProseMirror plugin tracks the
 * `/query` under the caret and owns keyboard nav; the `<SlashMenu>` React
 * component renders the list at the caret. Both read the shared NODE_CATALOG,
 * so the slash menu and the ribbon never drift.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey, type EditorState } from "@tiptap/pm/state";
import { useEffect, useReducer } from "react";
import type { Editor } from "@tiptap/react";

import {
    type CatalogEntry,
    filterEntries,
    insertEntry,
    rememberRecent,
} from "@/lib/dwi/node-catalog";

type SlashRange = { from: number; to: number };
type SlashState = {
    active: boolean;
    query: string;
    range: SlashRange | null;
    items: CatalogEntry[];
    index: number;
};

const EMPTY: SlashState = { active: false, query: "", range: null, items: [], index: 0 };

export const slashPluginKey = new PluginKey<SlashState>("dwiSlash");

/** Match a `/query` immediately before the caret, anchored at start-of-block
 *  or after whitespace (so `and/or` mid-word never triggers it). */
function matchSlash(state: EditorState): { query: string; range: SlashRange } | null {
    const { selection } = state;
    if (!selection.empty) return null;
    const $from = selection.$from;
    if (!$from.parent.isTextblock) return null;
    const textBefore = $from.parent.textBetween(0, $from.parentOffset, undefined, "￼");
    const m = /(?:^|\s)\/([\w-]*)$/.exec(textBefore);
    if (!m) return null;
    const query = m[1];
    const to = $from.pos;
    const from = to - query.length - 1; // include the leading slash
    return { query, range: { from, to } };
}

function applySelection(editor: Editor, range: SlashRange, entry: CatalogEntry) {
    editor.view.dispatch(editor.state.tr.setMeta(slashPluginKey, { type: "close" }));
    editor.chain().focus().deleteRange(range).run();
    insertEntry(editor, entry);
    rememberRecent(entry.id);
}

export const SlashCommand = Extension.create({
    name: "dwiSlashCommand",
    addProseMirrorPlugins() {
        return [
            new Plugin<SlashState>({
                key: slashPluginKey,
                state: {
                    init: () => EMPTY,
                    apply(tr, prev, _oldState, newState) {
                        const meta = tr.getMeta(slashPluginKey) as
                            | { type: "close" }
                            | { type: "move"; index: number }
                            | undefined;
                        if (meta?.type === "close") return EMPTY;

                        const match = matchSlash(newState);
                        if (!match) return EMPTY;

                        const items = filterEntries(match.query);
                        let index = prev.active ? prev.index : 0;
                        if (meta?.type === "move" && items.length) {
                            index = ((meta.index % items.length) + items.length) % items.length;
                        }
                        if (index >= items.length) index = 0;
                        return { active: true, query: match.query, range: match.range, items, index };
                    },
                },
                props: {
                    handleKeyDown(view, event) {
                        const st = slashPluginKey.getState(view.state);
                        if (!st?.active || st.items.length === 0) return false;
                        switch (event.key) {
                            case "ArrowDown":
                                view.dispatch(view.state.tr.setMeta(slashPluginKey, { type: "move", index: st.index + 1 }));
                                return true;
                            case "ArrowUp":
                                view.dispatch(view.state.tr.setMeta(slashPluginKey, { type: "move", index: st.index - 1 }));
                                return true;
                            case "Enter": {
                                const entry = st.items[st.index];
                                if (entry && st.range) applySelection(this.editor as Editor, st.range, entry);
                                return true;
                            }
                            case "Escape":
                                view.dispatch(view.state.tr.setMeta(slashPluginKey, { type: "close" }));
                                return true;
                            default:
                                return false;
                        }
                    },
                },
            }),
        ];
    },
});

/** Floating list rendered at the caret while a `/query` is active. Render once
 *  inside the engineer (editable) editor pane. */
export function SlashMenu({ editor }: { editor: Editor | null }) {
    const [, force] = useReducer((x: number) => x + 1, 0);

    useEffect(() => {
        if (!editor) return;
        const update = () => force();
        editor.on("transaction", update);
        return () => {
            editor.off("transaction", update);
        };
    }, [editor]);

    if (!editor) return null;
    const st = slashPluginKey.getState(editor.state);
    if (!st?.active || !st.range || st.items.length === 0) return null;

    const coords = editor.view.coordsAtPos(st.range.from);
    return (
        <div
            className="fixed z-50 max-h-72 w-64 overflow-auto rounded-md border bg-popover p-1 shadow-md"
            style={{ left: coords.left, top: coords.bottom + 4 }}
        >
            {st.items.map((entry, i) => (
                <button
                    key={entry.id}
                    type="button"
                    // onMouseDown + preventDefault so the editor keeps its
                    // selection (a plain onClick would blur first → range lost).
                    onMouseDown={(e) => {
                        e.preventDefault();
                        if (st.range) applySelection(editor, st.range, entry);
                    }}
                    className={
                        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left " +
                        (i === st.index ? "bg-accent text-accent-foreground" : "hover:bg-muted/60")
                    }
                >
                    <span className="shrink-0 text-muted-foreground">{entry.icon}</span>
                    <span className="min-w-0 flex-1">
                        <span className="block text-xs font-medium">{entry.label}</span>
                        <span className="block truncate text-[10px] text-muted-foreground">{entry.description}</span>
                    </span>
                </button>
            ))}
        </div>
    );
}
