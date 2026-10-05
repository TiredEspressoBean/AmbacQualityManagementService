import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LocationCombobox } from "@/components/locations/LocationCombobox";
import { useCreateStorageLocation, useUpdateStorageLocation } from "@/hooks/useReceivingMutations";
import type { LocationSummary } from "@/hooks/useLocations";
import type { Schema } from "@/lib/api/types";

type Kind = Schema<"StorageLocationKindEnum">;
/** What the dialog edits — a tree row or a location page both carry it. */
export type EditableLocation = Pick<LocationSummary,
    "id" | "name" | "parent" | "kind" | "code" | "description" | "held_only" | "receiving_dock" | "is_active">;

export const LOCATION_KINDS: { value: Kind; label: string }[] = [
    { value: "WAREHOUSE", label: "Warehouse" }, { value: "AREA", label: "Area" },
    { value: "RACK", label: "Rack" }, { value: "SHELF", label: "Shelf" }, { value: "BIN", label: "Bin" },
    { value: "CAGE", label: "Cage" }, { value: "YARD", label: "Yard" }, { value: "DOCK", label: "Dock" },
    { value: "CELL", label: "Work cell" }, { value: "LINE_SIDE", label: "Line-side" },
    { value: "OTHER", label: "Other" },
];

export const kindLabel = (k: string) => LOCATION_KINDS.find((x) => x.value === k)?.label ?? k;

const errorOf = (err: unknown, fallback: string) => {
    const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
    const first = data && Object.values(data)[0];
    return (Array.isArray(first) ? String(first[0]) : typeof first === "string" ? first : null) ?? fallback;
};

/**
 * Add or edit a location. ``location`` set: edit it. Otherwise a new one, under
 * ``parentId`` if given.
 */
export function LocationEditDialog({ open, onOpenChange, location, parentId }: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    location?: EditableLocation | null;
    parentId?: string | null;
}) {
    const create = useCreateStorageLocation();
    const update = useUpdateStorageLocation();
    const [name, setName] = useState("");
    const [parent, setParent] = useState<string | null>(null);
    const [kind, setKind] = useState<Kind>("OTHER");
    const [code, setCode] = useState("");
    const [description, setDescription] = useState("");
    const [heldOnly, setHeldOnly] = useState(false);
    const [dock, setDock] = useState(false);
    const [active, setActive] = useState(true);

    useEffect(() => {
        if (!open) return;
        setName(location?.name ?? "");
        setParent(location ? location.parent ?? null : parentId ?? null);
        setKind((location?.kind as Kind) ?? "OTHER");
        setCode(location?.code ?? "");
        setDescription(location?.description ?? "");
        setHeldOnly(location?.held_only ?? false);
        setDock(location?.receiving_dock ?? false);
        setActive(location?.is_active ?? true);
    }, [open, location, parentId]);

    const pending = create.isPending || update.isPending;
    const body = {
        name: name.trim(), parent, kind, code: code.trim(), description: description.trim(),
        held_only: heldOnly, receiving_dock: dock, is_active: active,
    };
    const save = () => {
        const done = {
            onSuccess: () => { toast.success(location ? "Saved." : `Added ${body.name}.`); onOpenChange(false); },
            onError: (e: unknown) => toast.error(errorOf(e, "Could not save the location")),
        };
        if (location) update.mutate({ id: location.id, ...body }, done);
        else create.mutate(body, done);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>{location ? `Edit ${location.name}` : "Add a location"}</DialogTitle>
                    <DialogDescription>
                        {location ? "Renaming a location renames it everywhere — what's in it stays in it."
                            : "A place things are kept: a warehouse, an area, a rack, a bin, a cage."}
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-3 py-1 sm:grid-cols-2">
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="loc-name">Name</Label>
                        <Input id="loc-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Rack 3" autoFocus />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label>Inside</Label>
                        <LocationCombobox value={parent} onChange={setParent} placeholder="Top level" className="w-full" />
                    </div>
                    <div className="space-y-1.5">
                        <Label>Kind</Label>
                        <Select value={kind} onValueChange={(v) => setKind(v as Kind)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {LOCATION_KINDS.map((k) => <SelectItem key={k.value} value={k.value}>{k.label}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="loc-code">Label code <span className="text-muted-foreground">(optional)</span></Label>
                        <Input id="loc-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. R3-B" />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="loc-desc">Description <span className="text-muted-foreground">(optional)</span></Label>
                        <Input id="loc-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
                    </div>
                    <label className="flex items-start gap-2 text-sm sm:col-span-2">
                        <Switch checked={heldOnly} onCheckedChange={setHeldOnly} disabled={dock} className="mt-0.5" />
                        <span>Held stock only<span className="block text-xs text-muted-foreground">
                            Only quarantined or rejected stock can be put here — an MRB or quarantine cage.{dock && " Not on a receiving dock."}</span></span>
                    </label>
                    <label className="flex items-start gap-2 text-sm sm:col-span-2">
                        <Switch checked={dock} onCheckedChange={setDock} disabled={heldOnly} className="mt-0.5" />
                        <span>Receiving dock<span className="block text-xs text-muted-foreground">
                            Deliveries go here unless the receiver says otherwise.{heldOnly && " Not on a held-only location."}</span></span>
                    </label>
                    {location && (
                        <label className="flex items-start gap-2 text-sm sm:col-span-2">
                            <Switch checked={active} onCheckedChange={setActive} className="mt-0.5" />
                            <span>In use<span className="block text-xs text-muted-foreground">
                                An inactive location takes nothing new; what's there stays.</span></span>
                        </label>
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
                    <Button onClick={save} disabled={pending || !name.trim()}>{pending ? "Saving…" : location ? "Save" : "Add"}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
