import { useState, useEffect } from "react";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    description?: string;
    label?: string;
    placeholder?: string;
    confirmLabel?: string;
    confirmVariant?: "default" | "destructive";
    required?: boolean;
    pending?: boolean;
    onSubmit: (text: string) => void;
};

export function ReasonPromptDialog({
    open,
    onOpenChange,
    title,
    description,
    label = "Reason",
    placeholder,
    confirmLabel = "Confirm",
    confirmVariant = "default",
    required = true,
    pending = false,
    onSubmit,
}: Props) {
    const [text, setText] = useState("");
    useEffect(() => { if (!open) setText(""); }, [open]);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    {description && <DialogDescription>{description}</DialogDescription>}
                </DialogHeader>
                <div className="space-y-2 py-2">
                    <Label htmlFor="reason-text">{label}{required && <span className="text-destructive"> *</span>}</Label>
                    <Textarea
                        id="reason-text"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder={placeholder}
                        rows={4}
                    />
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
                    <Button
                        variant={confirmVariant}
                        disabled={pending || (required && !text.trim())}
                        onClick={() => onSubmit(text)}
                    >
                        {pending ? "…" : confirmLabel}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
