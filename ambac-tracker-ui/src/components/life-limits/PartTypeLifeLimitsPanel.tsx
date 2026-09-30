/**
 * Life limits on the part type edit page: which life-limit definitions (cycles,
 * hours, shelf life…) apply to parts of this type, and whether each is required.
 *
 * Add / change / remove each show only for the matching model perm; the API
 * enforces the same.
 */
import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { DataIOButtons } from "@/components/data-io-buttons";
import {
    PART_TYPE_LIFE_LIMITS_KEY, useCreatePartTypeLifeLimit, useDeletePartTypeLifeLimit,
    useLifeLimitDefinitions, usePartTypeLifeLimits, useUpdatePartTypeLifeLimit,
    type PartTypeLifeLimit,
} from "@/hooks/usePartTypeLifeLimits";
import { toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

const fmtLimit = (v: string | null | undefined) => (v == null || v === "" ? "—" : String(Number(v)));

export function PartTypeLifeLimitsPanel({ partTypeId }: { partTypeId: string }) {
    const allows = useAllows();
    const canAdd = allows("add_parttypelifelimit");
    const canChange = allows("change_parttypelifelimit");
    const canDelete = allows("delete_parttypelifelimit");

    const { data: linksPage, isLoading } = usePartTypeLifeLimits(partTypeId);
    const { data: defsPage } = useLifeLimitDefinitions();
    const create = useCreatePartTypeLifeLimit();
    const update = useUpdatePartTypeLifeLimit();
    const del = useDeletePartTypeLifeLimit();

    const links = useMemo(() => linksPage?.results ?? [], [linksPage]);
    const definitions = useMemo(() => defsPage?.results ?? [], [defsPage]);
    const defById = useMemo(() => new Map(definitions.map((d) => [d.id, d])), [definitions]);
    const unlinked = useMemo(() => {
        const linked = new Set(links.map((l) => l.definition));
        return definitions.filter((d) => !linked.has(d.id));
    }, [links, definitions]);

    const [definition, setDefinition] = useState("");
    const [required, setRequired] = useState(true);
    const [removing, setRemoving] = useState<PartTypeLifeLimit | null>(null);

    function add() {
        if (!definition) return;
        create.mutate(
            { part_type: partTypeId, definition, is_required: required },
            {
                onSuccess: () => { setDefinition(""); setRequired(true); },
                onError: (e) => toastApiError(e, ["definition", "part_type", "non_field_errors"]),
            },
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between gap-2">
                    <div>
                        <CardTitle className="text-lg">Life Limits</CardTitle>
                        <CardDescription>
                            Which life limits parts of this type are tracked against. A required limit
                            must be tracked on every part of this type.
                        </CardDescription>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                        <DataIOButtons
                            endpoint="PartTypeLifeLimits"
                            displayName="Part Type Life Limits"
                            invalidateKeys={[[PART_TYPE_LIFE_LIMITS_KEY]]}
                            allowImport={canAdd || canChange}
                            queryParams={{ part_type: partTypeId }}
                        />
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {isLoading ? (
                    <p className="text-sm text-muted-foreground">Loading life limits…</p>
                ) : links.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No life limits apply to this part type.</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Life limit</TableHead>
                                <TableHead>Unit</TableHead>
                                <TableHead>Soft limit</TableHead>
                                <TableHead>Hard limit</TableHead>
                                <TableHead>Required</TableHead>
                                {canDelete && <TableHead className="w-12 text-right"><span className="sr-only">Remove</span></TableHead>}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {links.map((l) => {
                                const def = defById.get(l.definition);
                                return (
                                    <TableRow key={l.id}>
                                        <TableCell className="font-medium">{l.definition_name}</TableCell>
                                        <TableCell>{l.definition_unit || "—"}</TableCell>
                                        <TableCell>{fmtLimit(def?.soft_limit)}</TableCell>
                                        <TableCell>{fmtLimit(def?.hard_limit)}</TableCell>
                                        <TableCell>
                                            <Checkbox
                                                checked={l.is_required ?? true}
                                                disabled={!canChange || update.isPending}
                                                aria-label={`${l.definition_name} required`}
                                                onCheckedChange={(v) =>
                                                    update.mutate({ id: l.id, data: { is_required: v === true } })}
                                            />
                                        </TableCell>
                                        {canDelete && (
                                            <TableCell className="text-right">
                                                <Button variant="ghost" size="icon" className="text-destructive"
                                                    aria-label={`Remove ${l.definition_name}`} onClick={() => setRemoving(l)}>
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </TableCell>
                                        )}
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                )}

                {canAdd && (
                    <div className="flex flex-wrap items-end gap-3 border-t pt-4">
                        <div className="min-w-[220px] flex-1 space-y-1.5">
                            <Label>Add a life limit</Label>
                            <Select value={definition} onValueChange={(v) => v && setDefinition(v)}
                                {...(unlinked.length === 0 ? { disabled: true } : {})}>
                                <SelectTrigger aria-label="Life limit definition">
                                    <SelectValue placeholder={unlinked.length === 0 ? "Every definition is already linked" : "Select a definition"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {unlinked.map((d) => (
                                        <SelectItem key={d.id} value={d.id}>
                                            {d.name}{d.unit_label ? ` · ${d.unit_label}` : ""}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-center gap-2 pb-2">
                            <Checkbox id="ptll-required" checked={required} onCheckedChange={(v) => setRequired(v === true)} />
                            <Label htmlFor="ptll-required">Required</Label>
                        </div>
                        <Button size="sm" onClick={add} disabled={!definition || create.isPending}>
                            <Plus className="mr-1 h-4 w-4" /> Add
                        </Button>
                    </div>
                )}
            </CardContent>

            <AlertDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remove {removing?.definition_name}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            New parts of this type stop being tracked against it. Tracking already on
                            existing parts is kept.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => {
                                if (removing) del.mutate(removing.id);
                                setRemoving(null);
                            }}
                        >
                            Remove
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    );
}
