import { useState, type ReactNode, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/**
 * QuickComposer — the shared "quick authoring" input: a body field + an optional
 * trailing control (visibility toggle, audience select, …) + a Send button.
 * Manages its own draft text and clears on submit; Enter submits (Shift+Enter is
 * a newline when `multiline`). Consumers wire the mutation via `onSubmit`.
 *
 * This is the light path — for in-depth authoring (formatted prose, work
 * instructions) use the TipTap editor instead.
 */
export function QuickComposer({
    onSubmit,
    placeholder = "Add a note…",
    submitting = false,
    disabled = false,
    multiline = false,
    trailing,
}: {
    onSubmit: (text: string) => void;
    placeholder?: string;
    submitting?: boolean;
    disabled?: boolean;
    multiline?: boolean;
    /** Control(s) shown between the field and Send — e.g. a visibility toggle or audience select. */
    trailing?: ReactNode;
}) {
    const [text, setText] = useState("");
    const canSubmit = !!text.trim() && !submitting && !disabled;

    const submit = () => {
        if (!canSubmit) return;
        onSubmit(text.trim());
        setText("");
    };

    const onKeyDown = (e: KeyboardEvent) => {
        // Enter sends; Shift+Enter inserts a newline (only meaningful when multiline).
        if (e.key === "Enter" && (!multiline || !e.shiftKey)) {
            e.preventDefault();
            submit();
        }
    };

    return (
        <div className="flex gap-2">
            <div className="flex flex-1 gap-2">
                {multiline ? (
                    <Textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder={placeholder}
                        disabled={disabled}
                        rows={2}
                        className="flex-1 resize-none"
                    />
                ) : (
                    <Input
                        type="text"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        onKeyDown={onKeyDown}
                        placeholder={placeholder}
                        disabled={disabled}
                        className="flex-1"
                    />
                )}
                {trailing}
            </div>
            <Button size="icon" disabled={!canSubmit} onClick={submit} title="Send">
                <Send className="h-4 w-4" />
            </Button>
        </div>
    );
}

export default QuickComposer;
