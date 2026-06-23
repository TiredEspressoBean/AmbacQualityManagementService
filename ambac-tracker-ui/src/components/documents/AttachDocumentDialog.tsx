import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useRetrieveContentTypes } from "@/hooks/useRetrieveContentTypes";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { useRetrieveParts } from "@/hooks/parts";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { useRetrieveWorkOrders } from "@/hooks/useRetrieveWorkOrders";
import { useAttachDocument } from "@/hooks/useAttachDocument";

/**
 * Dialog for attaching a document to an additional entity (a secondary
 * association via DocumentLink). Curated to the common link targets; the
 * primary GFK owner is never affected. Gate the trigger on `add_documentlink`.
 */

const TARGET_MODELS = [
    { model: "orders", label: "Order" },
    { model: "parts", label: "Part" },
    { model: "parttypes", label: "Part Type" },
    { model: "workorder", label: "Work Order" },
] as const;

type TargetModel = (typeof TARGET_MODELS)[number]["model"];

function displayName(obj: any, model: TargetModel): string {
    switch (model) {
        case "orders":
            return obj.name || obj.order_number || `#${obj.id}`;
        case "workorder":
            return obj.ERP_id || obj.name || `#${obj.id}`;
        case "parttypes":
            return obj.name || `#${obj.id}`;
        case "parts":
            return obj.ERP_id || obj.name || `#${obj.id}`;
        default:
            return `#${obj.id}`;
    }
}

type AttachDocumentDialogProps = {
    documentId: string;
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

export function AttachDocumentDialog({ documentId, open, onOpenChange }: AttachDocumentDialogProps) {
    const [model, setModel] = useState<TargetModel | "">("");
    const [rawSearch, setRawSearch] = useState("");
    const [search, setSearch] = useState("");
    const attach = useAttachDocument();

    // Debounce the object search.
    useEffect(() => {
        const t = setTimeout(() => setSearch(rawSearch), 300);
        return () => clearTimeout(t);
    }, [rawSearch]);

    // Reset state whenever the dialog closes.
    useEffect(() => {
        if (!open) {
            setModel("");
            setRawSearch("");
            setSearch("");
        }
    }, [open]);

    // Map the selected model -> its ContentType id (what the attach endpoint needs).
    const { data: contentTypesRaw } = useRetrieveContentTypes({});
    const contentTypes = Array.isArray(contentTypesRaw) ? contentTypesRaw : [];
    const contentTypeId = contentTypes.find(
        (ct: { app_label?: string; model?: string; id?: number }) =>
            ct.app_label?.toLowerCase() === "tracker" && ct.model?.toLowerCase() === model,
    )?.id;

    const { data: orders } = useRetrieveOrders({ search }, undefined, { enabled: model === "orders" });
    const { data: parts } = useRetrieveParts({ search }, undefined, { enabled: model === "parts" });
    const { data: partTypes } = useRetrievePartTypes({ search }, undefined, { enabled: model === "parttypes" });
    const { data: workOrders } = useRetrieveWorkOrders({ search }, undefined, { enabled: model === "workorder" });

    const objects: any[] =
        model === "orders" ? orders?.results ?? []
            : model === "parts" ? parts?.results ?? []
                : model === "parttypes" ? partTypes?.results ?? []
                    : model === "workorder" ? workOrders?.results ?? []
                        : [];

    const handleAttach = (objectId: string) => {
        if (contentTypeId == null) {
            toast.error("Could not resolve the target type. Try again.");
            return;
        }
        attach.mutate(
            { id: documentId, contentType: contentTypeId, objectId },
            {
                onSuccess: () => {
                    toast.success("Document linked.");
                    onOpenChange(false);
                },
                onError: () => toast.error("Failed to link document."),
            },
        );
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Attach to another entity</DialogTitle>
                    <DialogDescription>
                        Create an additional association. This does not change the document's
                        primary owner.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-3">
                    <Select
                        value={model}
                        onValueChange={(v) => {
                            setModel(v as TargetModel);
                            setRawSearch("");
                            setSearch("");
                        }}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="Select entity type" />
                        </SelectTrigger>
                        <SelectContent>
                            {TARGET_MODELS.map((m) => (
                                <SelectItem key={m.model} value={m.model}>
                                    {m.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {model && (
                        <>
                            <Input
                                placeholder="Search…"
                                value={rawSearch}
                                onChange={(e) => setRawSearch(e.target.value)}
                            />
                            <ScrollArea className="h-64 rounded-md border">
                                <div className="p-1">
                                    {objects.map((obj) => {
                                        const isAttaching =
                                            attach.isPending &&
                                            attach.variables?.objectId === String(obj.id);
                                        return (
                                            <button
                                                key={obj.id}
                                                type="button"
                                                disabled={attach.isPending}
                                                onClick={() => handleAttach(String(obj.id))}
                                                className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm hover:bg-muted disabled:opacity-50"
                                            >
                                                <span>{displayName(obj, model)}</span>
                                                {isAttaching && <Loader2 className="h-4 w-4 animate-spin" />}
                                            </button>
                                        );
                                    })}
                                    {objects.length === 0 && (
                                        <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                                            No results
                                        </p>
                                    )}
                                </div>
                            </ScrollArea>
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
