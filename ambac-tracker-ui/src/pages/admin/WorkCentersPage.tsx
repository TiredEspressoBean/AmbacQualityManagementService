/**
 * Work Centers — admin surface for the routing/surface primitive that anchors
 * operator / QA / receiving / OSP work. See Documents/WORK_CENTER_DESIGN.md.
 *
 * List + inline create/edit dialog + archive. Tenants use this to model their
 * shop layout — each WC gets a `kind` (PRODUCTION / INSPECTION / RECEIVING /
 * OSP) that drives which surface a step lands on.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MapPin, MoreHorizontal, Plus, Search } from "lucide-react";

import { api } from "@/lib/api/generated";
import type { components } from "@/lib/api/generated-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type WorkCenter = components["schemas"]["WorkCenter"];
type Kind = "PRODUCTION" | "INSPECTION" | "RECEIVING" | "OSP";

const KIND_LABELS: Record<Kind, string> = {
    PRODUCTION: "Production",
    INSPECTION: "Inspection",
    RECEIVING: "Receiving",
    OSP: "OSP",
};
const KIND_TONE: Record<Kind, string> = {
    PRODUCTION: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
    INSPECTION: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200",
    RECEIVING: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200",
    OSP: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200",
};

type DraftState = {
    open: boolean;
    editing: WorkCenter | null;
    code: string;
    name: string;
    kind: Kind;
    description: string;
};

const EMPTY_DRAFT: DraftState = {
    open: false, editing: null, code: "", name: "", kind: "PRODUCTION", description: "",
};

export default function WorkCentersPage() {
    const qc = useQueryClient();
    const [search, setSearch] = useState("");
    const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);

    const { data: page, isLoading } = useQuery({
        queryKey: ["work-centers", "admin", search] as const,
        queryFn: () => api.api_WorkCenters_list({
            queries: { limit: 100, ...(search ? { search } : {}) },
        } as never),
    });
    const rows: WorkCenter[] = page?.results ?? [];

    const createMut = useMutation({
        mutationFn: (payload: { code: string; name: string; kind: Kind; description: string }) =>
            api.api_WorkCenters_create(payload as never),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["work-centers"] });
            toast.success("Work center created.");
            setDraft(EMPTY_DRAFT);
        },
        onError: (e: unknown) => toast.error(`Couldn't create: ${(e as Error).message}`),
    });
    const updateMut = useMutation({
        mutationFn: ({ id, ...payload }: { id: string; code: string; name: string; kind: Kind; description: string }) =>
            api.api_WorkCenters_partial_update(payload as never, { params: { id } }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["work-centers"] });
            toast.success("Work center updated.");
            setDraft(EMPTY_DRAFT);
        },
        onError: (e: unknown) => toast.error(`Couldn't update: ${(e as Error).message}`),
    });
    const archiveMut = useMutation({
        mutationFn: (id: string) =>
            api.api_WorkCenters_partial_update({ archived: true } as never, { params: { id } }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["work-centers"] });
            toast.success("Archived.");
        },
    });

    const openCreate = () => setDraft({ ...EMPTY_DRAFT, open: true });
    const openEdit = (wc: WorkCenter) => setDraft({
        open: true, editing: wc,
        code: wc.code, name: wc.name,
        // WorkCenter.kind isn't yet on the read-serializer for older tenants;
        // fall back to PRODUCTION defensively.
        kind: (((wc as unknown) as { kind?: Kind }).kind ?? "PRODUCTION"),
        description: wc.description ?? "",
    });

    const submit = () => {
        const payload = {
            code: draft.code.trim(), name: draft.name.trim(),
            kind: draft.kind, description: draft.description.trim(),
        };
        if (!payload.code || !payload.name) {
            toast.error("Code and name are required.");
            return;
        }
        if (draft.editing) updateMut.mutate({ id: draft.editing.id, ...payload });
        else createMut.mutate(payload);
    };

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-4">
            <div className="flex items-center gap-3">
                <h1 className="flex min-w-0 flex-1 items-center gap-2 truncate text-2xl font-semibold tracking-tight">
                    <MapPin className="h-6 w-6 text-muted-foreground" /> Work Centers
                </h1>
                <div className="relative w-64">
                    <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        className="pl-8"
                        placeholder="Search name or code…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <Button onClick={openCreate}>
                    <Plus className="mr-1 h-4 w-4" /> New work center
                </Button>
            </div>

            <p className="text-sm text-muted-foreground">
                Work centers are how steps and users route to the right surface. Each work center's{" "}
                <b className="text-foreground">kind</b> determines whether its work appears on the operator
                queue, the QA inbox, the receiving inbox, or the OSP dispatch.
            </p>

            <div className="overflow-hidden rounded-md border">
                <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <tr>
                            <th className="px-3 py-2">Code</th>
                            <th className="px-3 py-2">Name</th>
                            <th className="px-3 py-2">Kind</th>
                            <th className="px-3 py-2">Description</th>
                            <th className="w-10 px-3 py-2"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading && (
                            <tr><td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">Loading…</td></tr>
                        )}
                        {!isLoading && rows.length === 0 && (
                            <tr><td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                                No work centers yet. Click "New work center" to add one.
                            </td></tr>
                        )}
                        {rows.map((wc) => {
                            const kind = (((wc as unknown) as { kind?: Kind }).kind ?? "PRODUCTION");
                            const archived = ((wc as unknown) as { archived?: boolean }).archived;
                            return (
                                <tr key={wc.id} className={`border-t ${archived ? "opacity-50" : ""}`}>
                                    <td className="px-3 py-2 font-mono text-xs">{wc.code}</td>
                                    <td className="px-3 py-2 font-medium">
                                        {wc.name}
                                        {archived && <Badge variant="outline" className="ml-2 text-[10px]">Archived</Badge>}
                                    </td>
                                    <td className="px-3 py-2">
                                        <Badge className={KIND_TONE[kind]}>{KIND_LABELS[kind]}</Badge>
                                    </td>
                                    <td className="px-3 py-2 text-muted-foreground">{wc.description || "—"}</td>
                                    <td className="px-3 py-2">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem onClick={() => openEdit(wc)}>Edit</DropdownMenuItem>
                                                {!archived && (
                                                    <DropdownMenuItem
                                                        className="text-destructive"
                                                        onClick={() => archiveMut.mutate(wc.id)}
                                                    >
                                                        Archive
                                                    </DropdownMenuItem>
                                                )}
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <Dialog open={draft.open} onOpenChange={(v) => !v && setDraft(EMPTY_DRAFT)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>{draft.editing ? "Edit work center" : "New work center"}</DialogTitle>
                        <DialogDescription>
                            Give it a short code (used in step-editor pickers) and pick the kind of work
                            it does — that's what routes work to the right surface.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="wc-code">Code</Label>
                                <Input id="wc-code" value={draft.code}
                                    onChange={(e) => setDraft({ ...draft, code: e.target.value })}
                                    placeholder="PROD-01" />
                            </div>
                            <div className="col-span-2 space-y-1.5">
                                <Label htmlFor="wc-name">Name</Label>
                                <Input id="wc-name" value={draft.name}
                                    onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                                    placeholder="Production Floor" />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="wc-kind">Kind</Label>
                            <Select
                                value={draft.kind}
                                onValueChange={(v) => setDraft({ ...draft, kind: v as Kind })}
                            >
                                <SelectTrigger id="wc-kind"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="PRODUCTION">Production — the operator queue</SelectItem>
                                    <SelectItem value="INSPECTION">Inspection — the QA inbox</SelectItem>
                                    <SelectItem value="RECEIVING">Receiving — the receiving inbox</SelectItem>
                                    <SelectItem value="OSP">OSP — outside processing dispatch</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="wc-desc">Description</Label>
                            <Textarea id="wc-desc" value={draft.description} rows={2}
                                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                                placeholder="Optional context — what happens here, who works here…" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setDraft(EMPTY_DRAFT)}>Cancel</Button>
                        <Button
                            onClick={submit}
                            disabled={createMut.isPending || updateMut.isPending}
                        >
                            {draft.editing ? "Save" : "Create"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
