/**
 * Machine eligibility edited from its owner's side: the machines that can run one
 * step (on the step editor), or the steps one machine can run (on the equipment
 * form). Same rows either way — a StepEquipmentAffinity is the pair.
 *
 * Each add / change / remove saves at once and shows only for the matching perm.
 */
import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
    useCreateStepAffinity, useDeleteStepAffinity, useStepAffinities, useUpdateStepAffinity,
    type StepEquipmentAffinity,
} from "@/hooks/useSchedulingSetup";
import type { components } from "@/lib/api/generated-types";
import {
    AFFINITY_LABEL, EquipmentSelect, StepSelect, toastApiError, useAllows,
} from "@/pages/scheduling/setup/shared";

type Affinity = components["schemas"]["AffinityEnum"];

type Owner = { step: string; equipment?: never } | { equipment: string; step?: never };

function parseOverride(raw: string): number | null | undefined {
    if (raw.trim() === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? n : undefined;
}

export function MachineEligibilityTable({ owner, readOnly = false }: { owner: Owner; readOnly?: boolean }) {
    const allows = useAllows();
    const canAdd = !readOnly && allows("add_stepequipmentaffinity");
    const canChange = !readOnly && allows("change_stepequipmentaffinity");
    const canDelete = !readOnly && allows("delete_stepequipmentaffinity");
    const byStep = owner.step !== undefined;

    const { data, isLoading } = useStepAffinities(
        byStep ? { step: owner.step, limit: 200 } : { equipment: owner.equipment, limit: 200 },
    );
    const rows = useMemo(() => data?.results ?? [], [data]);
    const create = useCreateStepAffinity();
    const update = useUpdateStepAffinity();
    const del = useDeleteStepAffinity();

    const [other, setOther] = useState("");
    const [affinity, setAffinity] = useState<Affinity>("eligible");
    const [override, setOverride] = useState("");

    function add() {
        if (!other) return;
        const cycle = parseOverride(override);
        if (cycle === undefined) {
            toastApiError(new Error("Cycle override must be minutes, 0 or more — or blank"));
            return;
        }
        const payload = byStep
            ? { step: owner.step!, equipment: other, affinity, cycle_time_override: cycle }
            : { step: other, equipment: owner.equipment!, affinity, cycle_time_override: cycle };
        create.mutate(payload, {
            onSuccess: () => { setOther(""); setAffinity("eligible"); setOverride(""); },
            onError: (e) => toastApiError(e, ["step", "equipment", "cycle_time_override", "non_field_errors"]),
        });
    }

    function remove(row: StepEquipmentAffinity) {
        const label = byStep ? row.equipment_name : row.step_name;
        if (window.confirm(`Remove ${label}? The scheduler stops placing this step on that machine.`)) {
            del.mutate(row.id, { onError: (e) => toastApiError(e) });
        }
    }

    return (
        <div className="space-y-4">
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                    {byStep
                        ? "No machines listed. The scheduler can't place this step until one is."
                        : "This machine isn't listed for any step yet."}
                </p>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>{byStep ? "Machine" : "Step"}</TableHead>
                            <TableHead className="w-48">How well</TableHead>
                            <TableHead className="w-32">Cycle override</TableHead>
                            {canDelete && <TableHead className="w-12"><span className="sr-only">Remove</span></TableHead>}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((r) => (
                            <TableRow key={r.id}>
                                <TableCell className="font-medium">{byStep ? r.equipment_name : r.step_name}</TableCell>
                                <TableCell>
                                    <Select
                                        value={r.affinity ?? "eligible"}
                                        onValueChange={(v) => v && update.mutate(
                                            { id: r.id, data: { affinity: v as Affinity } },
                                            { onError: (e) => toastApiError(e) },
                                        )}
                                        {...(!canChange ? { disabled: true } : {})}
                                    >
                                        <SelectTrigger className="h-8" aria-label="How well it runs the step"><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {Object.entries(AFFINITY_LABEL).map(([value, label]) => (
                                                <SelectItem key={value} value={value}>{label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </TableCell>
                                <TableCell className="tabular-nums text-muted-foreground">
                                    {r.cycle_time_override == null ? "Standard" : `${r.cycle_time_override} min`}
                                </TableCell>
                                {canDelete && (
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="icon" className="text-destructive"
                                            aria-label={`Remove ${byStep ? r.equipment_name : r.step_name}`}
                                            onClick={() => remove(r)}>
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </TableCell>
                                )}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            )}

            {canAdd && (
                <div className="grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_11rem_8rem_auto] sm:items-end">
                    <div className="space-y-1.5">
                        <Label>{byStep ? "Add a machine" : "Add a step"}</Label>
                        {byStep
                            ? <EquipmentSelect value={other} onChange={setOther} />
                            : <StepSelect value={other} onChange={setOther} />}
                    </div>
                    <div className="space-y-1.5">
                        <Label>How well</Label>
                        <Select value={affinity} onValueChange={(v) => v && setAffinity(v as Affinity)}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                {Object.entries(AFFINITY_LABEL).map(([value, label]) => (
                                    <SelectItem key={value} value={value}>{label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor={`me-cycle-${owner.step ?? owner.equipment}`}>Cycle (min)</Label>
                        <Input id={`me-cycle-${owner.step ?? owner.equipment}`} type="number" min={0} step="any"
                            inputMode="decimal" placeholder="Standard"
                            value={override} onChange={(e) => setOverride(e.target.value)} />
                    </div>
                    <Button size="sm" className="h-9" onClick={add} disabled={!other || create.isPending}>
                        <Plus className="mr-1 h-4 w-4" /> Add
                    </Button>
                </div>
            )}
        </div>
    );
}
