import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ExternalLink, Plus, Tag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
    useCreateStorageLocation, useStorageLocations, useUpdateStorageLocation,
} from "@/hooks/useReceivingMutations";
import { useReportEmail } from "@/hooks/useReportEmail";
import type { Schema } from "@/lib/api/types";

type Loc = Schema<"StorageLocation">;

const errorOf = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { detail?: string; name?: string[] } } })?.response?.data?.name?.[0]
    ?? (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;

function LocationRow({ loc }: { loc: Loc }) {
    const [name, setName] = useState(loc.name);
    const [description, setDescription] = useState(loc.description ?? "");
    const update = useUpdateStorageLocation();
    const { downloadReport } = useReportEmail();
    const dirty = name.trim() !== loc.name || description.trim() !== (loc.description ?? "");
    const save = () => update.mutate({ id: String(loc.id), name: name.trim(), description: description.trim() }, {
        onSuccess: () => toast.success("Saved"),
        onError: (e) => toast.error(errorOf(e, "Could not save")),
    });
    return (
        <div className="flex flex-wrap items-center gap-2 border-b py-2 last:border-0">
            <Input className="w-48" value={name} onChange={(e) => setName(e.target.value)} aria-label="Name" />
            <Input className="min-w-48 flex-1" value={description} placeholder="Description (optional)"
                onChange={(e) => setDescription(e.target.value)} aria-label="Description" />
            {dirty && <Button size="sm" onClick={save} disabled={!name.trim() || update.isPending}>Save</Button>}
            <div className="flex items-center gap-2">
                <Switch checked={loc.is_active ?? true} aria-label="Active"
                    onCheckedChange={(c) => update.mutate({ id: String(loc.id), is_active: c })} />
                {!(loc.is_active ?? true) && <Badge variant="outline">Inactive</Badge>}
            </div>
            <Button size="sm" variant="ghost" aria-label={`Print a label for ${loc.name}`}
                onClick={() => void downloadReport("location_label", { names: [loc.name], copies: 1, layout: "thermal" })}>
                <Tag className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost" asChild aria-label={`Open ${loc.name}`}>
                <Link to="/production/locations/$name" params={{ name: loc.name }}><ExternalLink className="h-4 w-4" /></Link>
            </Button>
        </div>
    );
}

/**
 * The tenant's list of places stock is put away. Optional: with none here, receiving
 * takes any location typed and suggests ones used before. Once there are entries,
 * receiving offers only the active ones — so "Rack 3", "rack3" and "R3" stop being
 * three places, and moves must go to one of them. Renaming one carries what's in it
 * across. Flat on purpose; aisle/bin structure is warehouse management.
 */
export function StorageLocationsEditorPage() {
    const { data, isLoading } = useStorageLocations();
    const create = useCreateStorageLocation();
    const [name, setName] = useState("");
    const locations = data?.results ?? [];

    const add = () => create.mutate({ name: name.trim() }, {
        onSuccess: () => { setName(""); toast.success("Location added"); },
        onError: (e) => toast.error(errorOf(e, "Could not add the location")),
    });

    return (
        <div className="mx-auto max-w-3xl space-y-4 p-6">
            <div>
                <h1 className="text-2xl font-semibold tracking-tight">Storage locations</h1>
                <p className="text-sm text-muted-foreground">
                    Optional. Leave this empty and receiving accepts any location typed. Add
                    locations here and receiving offers only these, so every lot is put away
                    somewhere with one name.
                </p>
            </div>
            <Card>
                <CardContent className="pt-6">
                    <form className="mb-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) add(); }}>
                        <Input placeholder="e.g. Rack 3" value={name} onChange={(e) => setName(e.target.value)}
                            aria-label="New location name" />
                        <Button type="submit" disabled={!name.trim() || create.isPending}>
                            <Plus className="mr-1 h-4 w-4" /> Add
                        </Button>
                    </form>
                    {isLoading ? (
                        <div className="h-24 animate-pulse rounded bg-muted" />
                    ) : locations.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No managed locations — receiving takes free text.</p>
                    ) : (
                        locations.map((l) => <LocationRow key={String(l.id)} loc={l} />)
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
