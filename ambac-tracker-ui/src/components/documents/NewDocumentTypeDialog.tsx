import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useCreateDocumentType } from "@/hooks/useCreateDocumentType";
import type { Schema } from "@/lib/api/types";

type CreatedDocumentType = Schema<"DocumentType">;

/**
 * Inline "create new document type" dialog.
 *
 * Lives inside the Document upload form so a user picking a Document
 * Type can author a new option without leaving the page. Collects only
 * the two fields the model marks required (`name`, `code`) plus a
 * description and the `requires_approval` toggle — the rest of
 * DocumentType's compliance fields (review period, retention, approval
 * template, etc.) stay on the dedicated DocumentType admin form.
 *
 * On success the hook invalidates the documentTypes list query so the
 * combobox below this dialog refetches with the new option included.
 * The parent's `onCreated` callback receives the new id so it can
 * auto-select it.
 */
type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: (documentType: CreatedDocumentType) => void;
    initialName?: string;
};

export function NewDocumentTypeDialog({
    open,
    onOpenChange,
    onCreated,
    initialName,
}: Props) {
    const [name, setName] = useState("");
    const [code, setCode] = useState("");
    const [description, setDescription] = useState("");
    const [requiresApproval, setRequiresApproval] = useState(true);

    const createDocumentType = useCreateDocumentType();

    // When the dialog opens with a pre-typed name (the search string
    // from the parent combobox), seed it in and derive a default code.
    useEffect(() => {
        if (open) {
            const seed = initialName?.trim() ?? "";
            setName(seed);
            if (seed) {
                setCode(
                    seed
                        .toUpperCase()
                        .replace(/[^A-Z0-9]+/g, "")
                        .slice(0, 6) || ""
                );
            } else {
                setCode("");
            }
            setDescription("");
            setRequiresApproval(true);
        }
    }, [open, initialName]);

    const canSubmit =
        name.trim().length > 0 &&
        code.trim().length > 0 &&
        !createDocumentType.isPending;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;
        try {
            const created = await createDocumentType.mutateAsync({
                name: name.trim(),
                code: code.trim(),
                description: description.trim() || undefined,
                requires_approval: requiresApproval,
            } as Parameters<typeof createDocumentType.mutateAsync>[0]);
            toast.success(`Created document type ${created.code}`);
            onOpenChange(false);
            onCreated(created as CreatedDocumentType);
        } catch (err) {
            console.error("Create document type failed", err);
            toast.error("Failed to create document type.");
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>New Document Type</DialogTitle>
                        <DialogDescription>
                            Create a new category for documents. You can refine
                            review and retention defaults later from the
                            Document Types admin page.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="doc-type-name">
                                Name <span className="text-destructive">*</span>
                            </Label>
                            <Input
                                id="doc-type-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. Standard Operating Procedure"
                                autoFocus
                                maxLength={100}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="doc-type-code">
                                Code <span className="text-destructive">*</span>
                            </Label>
                            <Input
                                id="doc-type-code"
                                value={code}
                                onChange={(e) => setCode(e.target.value.toUpperCase())}
                                placeholder="e.g. SOP"
                                maxLength={20}
                            />
                            <p className="text-xs text-muted-foreground">
                                Short prefix used in document IDs.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="doc-type-description">Description</Label>
                            <Textarea
                                id="doc-type-description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Optional details about when this category applies"
                                rows={3}
                            />
                        </div>

                        <div className="flex items-start gap-2">
                            <Checkbox
                                id="doc-type-requires-approval"
                                checked={requiresApproval}
                                onCheckedChange={(v) => setRequiresApproval(v === true)}
                            />
                            <div className="grid gap-0.5 leading-none">
                                <Label
                                    htmlFor="doc-type-requires-approval"
                                    className="font-normal cursor-pointer"
                                >
                                    Requires approval
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    Documents of this type must go through an
                                    approval workflow before release.
                                </p>
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={!canSubmit}>
                            {createDocumentType.isPending ? "Creating…" : "Create"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
