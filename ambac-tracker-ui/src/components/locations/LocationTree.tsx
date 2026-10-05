import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronDown, ChevronRight, GripVertical, Pencil, Plus, Tag, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { LocationEditDialog, kindLabel } from "@/components/locations/LocationEditDialog";
import { locationSummaryOptions, type LocationSummary } from "@/hooks/useLocations";
import { usePermissionSet } from "@/hooks/useMyPermissions";
import { useDeleteStorageLocation, useUpdateStorageLocation } from "@/hooks/useReceivingMutations";
import { useReportEmail } from "@/hooks/useReportEmail";

const errorOf = (err: unknown, fallback: string) => {
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    if (Array.isArray(data)) return String(data[0]);
    return (data as { detail?: string })?.detail ?? fallback;
};

const count = (own: number, total: number) =>
    total === 0 ? "—" : own === total ? String(total) : `${total} (${own} here)`;

/**
 * The tenant's locations as a tree: counts roll up (a rack shows what's in its bins),
 * rows open the location, ticked rows print labels. Anyone who may change locations can
 * edit a row, or drag it onto another to put it inside that one (or onto the top-level
 * strip to take it out). With ``manage`` (Data Management), an empty row can be removed.
 */
export function LocationTree({ manage = false }: { manage?: boolean }) {
    const { data, isLoading } = useQuery(locationSummaryOptions());
    const { has } = usePermissionSet();
    const { downloadReport } = useReportEmail();
    const remove = useDeleteStorageLocation();
    const update = useUpdateStorageLocation();
    const [dragging, setDragging] = useState<LocationSummary | null>(null);
    const [over, setOver] = useState<string | null>(null);  // a row id, or "ROOT"
    const [filter, setFilter] = useState("");
    const [showInactive, setShowInactive] = useState(false);
    const [closed, setClosed] = useState<Set<string>>(new Set());
    const [picked, setPicked] = useState<Set<string>>(new Set());
    const [editing, setEditing] = useState<{ location?: LocationSummary | null; parentId?: string | null } | null>(null);

    const canAdd = has("add_storagelocation");
    const canEdit = has("change_storagelocation");
    const canDelete = manage && has("delete_storagelocation");

    const rows = useMemo(() => {
        const all = (data ?? []).filter((r) => showInactive || r.is_active);
        const q = filter.trim().toLowerCase();
        if (q) return all.filter((r) => r.path.toLowerCase().includes(q) || r.code.toLowerCase().includes(q));
        // Hide the descendants of a collapsed row.
        const byId = new Map(all.map((r) => [r.id, r]));
        const hidden = (r: LocationSummary) => {
            let p = r.parent ? byId.get(r.parent) : undefined;
            for (let i = 0; p && i < 12; i++) {
                if (closed.has(p.id)) return true;
                p = p.parent ? byId.get(p.parent) : undefined;
            }
            return false;
        };
        return all.filter((r) => !hidden(r));
    }, [data, filter, closed, showInactive]);
    const hasChildren = useMemo(() => new Set((data ?? []).map((r) => r.parent).filter(Boolean) as string[]), [data]);

    // A row can't go inside itself or anything inside it (the server refuses too).
    const insideOf = useMemo(() => {
        const byId = new Map((data ?? []).map((r) => [r.id, r]));
        return (id: string, ancestor: string) => {
            let node = byId.get(id);
            for (let i = 0; node && i < 50; i++) {
                if (node.id === ancestor) return true;
                node = node.parent ? byId.get(node.parent) : undefined;
            }
            return false;
        };
    }, [data]);
    const canDropOn = (target: string | null) =>
        !!dragging && dragging.parent !== target && (target === null || !insideOf(target, dragging.id));
    const reparent = (target: LocationSummary | null) => {
        const moving = dragging;
        setDragging(null); setOver(null);
        if (!moving || !canDropOn(target?.id ?? null)) return;
        update.mutate({ id: moving.id, parent: target?.id ?? null }, {
            onSuccess: () => toast.success(target ? `${moving.name} is now inside ${target.name}.` : `${moving.name} is now top-level.`),
            onError: (e) => toast.error(errorOf(e, "Could not move it")),
        });
    };

    const toggle = (set: Set<string>, id: string) => { const x = new Set(set); if (x.has(id)) x.delete(id); else x.add(id); return x; };
    const printLabels = (ids: string[]) =>
        void downloadReport("location_label", { names: ids, copies: 1, layout: ids.length > 2 ? "sheet" : "thermal" })
            .then(() => toast.success(`Labels for ${ids.length} location${ids.length === 1 ? "" : "s"}.`));

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
                <Input placeholder="Filter by name, path or code…" value={filter} onChange={(e) => setFilter(e.target.value)} className="max-w-xs" />
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Checkbox checked={showInactive} onCheckedChange={(c) => setShowInactive(c === true)} /> Show inactive
                </label>
                <div className="ml-auto flex gap-2">
                    {canAdd && (
                        <Button size="sm" variant="outline" onClick={() => setEditing({ location: null, parentId: null })}>
                            <Plus className="mr-1 h-4 w-4" /> Add location
                        </Button>
                    )}
                    <Button size="sm" variant="outline" disabled={picked.size === 0} onClick={() => printLabels([...picked])}>
                        <Tag className="mr-1 h-4 w-4" /> Print labels{picked.size ? ` (${picked.size})` : ""}
                    </Button>
                </div>
            </div>

            {/* Always rendered: a drop zone that appears when a drag starts shifts the
                rows under the pointer, and the browser cancels the drag. */}
            {canEdit && !filter && (
                <div onDragOver={(e) => { if (canDropOn(null)) { e.preventDefault(); setOver("ROOT"); } }}
                    onDragLeave={() => setOver((o) => (o === "ROOT" ? null : o))}
                    onDrop={(e) => { e.preventDefault(); reparent(null); }}
                    className={`rounded-lg border-2 border-dashed px-3 py-2 text-center text-xs ${over === "ROOT"
                        ? "border-primary bg-primary/10 text-foreground" : "text-muted-foreground"}`}>
                    {dragging?.parent
                        ? <>Drop here to take <strong>{dragging.name}</strong> out — it becomes top-level</>
                        : "Drag a location onto another to put it inside it, or here to make it top-level."}
                </div>
            )}

            <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b text-left text-muted-foreground">
                            <th className="w-8 px-3 py-2" />
                            <th className="px-3 py-2 font-medium">Location</th>
                            <th className="px-3 py-2 font-medium">Kind</th>
                            <th className="px-3 py-2 text-right font-medium">Lots</th>
                            <th className="px-3 py-2 text-right font-medium">Units</th>
                            <th className="px-3 py-2 text-right font-medium">Machines</th>
                            {(canEdit || canDelete || canAdd) && <th className="w-28 px-3 py-2" />}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r) => {
                            const isOpen = !closed.has(r.id);
                            const empty = r.total_lots + r.total_parts + r.total_equipment === 0;
                            return (
                                <tr key={r.id}
                                    className={`border-b last:border-0 ${over === r.id ? "bg-primary/10 outline outline-2 -outline-offset-2 outline-primary" : ""} ${dragging?.id === r.id ? "opacity-50" : ""}`}
                                    draggable={canEdit && !filter}
                                    onDragStart={(e) => {
                                        e.dataTransfer.effectAllowed = "move";
                                        e.dataTransfer.setData("text/plain", r.id);
                                        // After the drag has begun: re-rendering inside dragstart can cancel it.
                                        setTimeout(() => setDragging(r), 0);
                                    }}
                                    onDragEnd={() => { setDragging(null); setOver(null); }}
                                    onDragOver={(e) => { if (canDropOn(r.id)) { e.preventDefault(); setOver(r.id); } }}
                                    onDragLeave={() => setOver((o) => (o === r.id ? null : o))}
                                    onDrop={(e) => { e.preventDefault(); reparent(r); }}>
                                    <td className="px-3 py-2">
                                        <div className="flex items-center gap-1">
                                            {canEdit && !filter && <GripVertical className="h-4 w-4 cursor-grab text-muted-foreground" aria-hidden />}
                                            <Checkbox checked={picked.has(r.id)} onCheckedChange={() => setPicked((s) => toggle(s, r.id))}
                                                aria-label={`Label for ${r.name}`} />
                                        </div>
                                    </td>
                                    <td className="px-3 py-2">
                                        <div className="flex items-center gap-1" style={{ paddingLeft: filter ? 0 : r.depth * 20 }}>
                                            {!filter && hasChildren.has(r.id) ? (
                                                <button type="button" className="text-muted-foreground" aria-label={isOpen ? "Collapse" : "Expand"}
                                                    onClick={() => setClosed((s) => toggle(s, r.id))}>
                                                    {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                                </button>
                                            ) : <span className="inline-block w-4" />}
                                            <Link to="/production/locations/$locationId" params={{ locationId: r.id }} className="font-medium hover:underline">
                                                {filter ? r.path : r.name}
                                            </Link>
                                            {r.code && <span className="font-mono text-xs text-muted-foreground">{r.code}</span>}
                                            {r.held_only && <Badge variant="outline" className="text-xs">Held only</Badge>}
                                            {r.receiving_dock && <Badge variant="outline" className="text-xs">Receiving dock</Badge>}
                                            {!r.is_active && <Badge variant="secondary" className="text-xs">Inactive</Badge>}
                                        </div>
                                        {r.description && <div className="text-xs text-muted-foreground" style={{ paddingLeft: filter ? 0 : r.depth * 20 + 20 }}>{r.description}</div>}
                                    </td>
                                    <td className="px-3 py-2 text-muted-foreground">{kindLabel(r.kind)}</td>
                                    <td className="px-3 py-2 text-right tabular-nums">{count(r.lots, r.total_lots)}</td>
                                    <td className="px-3 py-2 text-right tabular-nums">{count(r.parts, r.total_parts)}</td>
                                    <td className="px-3 py-2 text-right tabular-nums">{count(r.equipment, r.total_equipment)}</td>
                                    {(canEdit || canDelete || canAdd) && (
                                        <td className="px-3 py-2">
                                            <div className="flex justify-end gap-1">
                                                {canAdd && (
                                                    <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Add a location inside ${r.name}`}
                                                        onClick={() => setEditing({ location: null, parentId: r.id })}>
                                                        <Plus className="h-4 w-4" />
                                                    </Button>
                                                )}
                                                {canEdit && (
                                                    <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Edit ${r.name}`}
                                                        onClick={() => setEditing({ location: r })}>
                                                        <Pencil className="h-4 w-4" />
                                                    </Button>
                                                )}
                                                {canDelete && empty && !hasChildren.has(r.id) && (
                                                    <Button size="icon" variant="ghost" className="h-7 w-7" aria-label={`Remove ${r.name}`}
                                                        onClick={() => remove.mutate(r.id, {
                                                            onSuccess: () => toast.success(`Removed ${r.name}.`),
                                                            onError: (e) => toast.error(errorOf(e, "Could not remove it")),
                                                        })}>
                                                        <Trash2 className="h-4 w-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </td>
                                    )}
                                </tr>
                            );
                        })}
                        {!isLoading && rows.length === 0 && (
                            <tr><td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">
                                {filter ? "No location matches." : "No locations yet. Add the places stock is kept — a warehouse, its racks, their bins."}
                            </td></tr>
                        )}
                    </tbody>
                </table>
            </div>
            <LocationEditDialog open={editing !== null} onOpenChange={(o) => { if (!o) setEditing(null); }}
                location={editing?.location} parentId={editing?.parentId} />
        </div>
    );
}
