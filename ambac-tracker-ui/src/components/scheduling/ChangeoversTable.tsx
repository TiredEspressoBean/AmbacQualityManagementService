/**
 * One machine's changeover matrix, edited on the equipment form: minutes to switch
 * the machine from running one step to another. Each row saves at once.
 */
import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
    useChangeovers, useCreateChangeover, useDeleteChangeover, useUpdateChangeover,
    type WorkCenterChangeover,
} from "@/hooks/useSchedulingSetup";
import { StepSelect, parseMinutes, toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

function MinutesCell({ row, canChange }: { row: WorkCenterChangeover; canChange: boolean }) {
    const update = useUpdateChangeover();
    const [value, setValue] = useState(String(row.changeover_minutes ?? 0));
    if (!canChange) return <span className="tabular-nums">{row.changeover_minutes ?? 0} min</span>;
    return (
        <Input
            type="number" min={0} step="any" inputMode="decimal" className="h-8 w-24"
            aria-label={`Changeover minutes, ${row.from_step_name} to ${row.to_step_name}`}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => {
                const n = parseMinutes(value, "Changeover");
                if (n === null || n === (row.changeover_minutes ?? 0)) return;
                update.mutate({ id: row.id, data: { changeover_minutes: n } }, { onError: (e) => toastApiError(e) });
            }}
        />
    );
}

export function ChangeoversTable({ equipmentId }: { equipmentId: string }) {
    const allows = useAllows();
    const canAdd = allows("add_workcenterchangeover");
    const canChange = allows("change_workcenterchangeover");
    const canDelete = allows("delete_workcenterchangeover");

    const { data, isLoading } = useChangeovers({ equipment: equipmentId, limit: 500 });
    const rows = useMemo(() => data?.results ?? [], [data]);
    const create = useCreateChangeover();
    const del = useDeleteChangeover();

    const [fromStep, setFromStep] = useState("");
    const [toStep, setToStep] = useState("");
    const [minutes, setMinutes] = useState("");

    function add() {
        if (!fromStep || !toStep) return;
        const n = parseMinutes(minutes, "Changeover");
        if (n === null) return;
        create.mutate(
            { equipment: equipmentId, from_step: fromStep, to_step: toStep, changeover_minutes: n },
            {
                onSuccess: () => { setFromStep(""); setToStep(""); setMinutes(""); },
                onError: (e) => toastApiError(e, ["from_step", "to_step", "changeover_minutes", "non_field_errors"]),
            },
        );
    }

    return (
        <div className="space-y-4">
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
            ) : rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                    No changeovers. Switching between steps on this machine is treated as free.
                </p>
            ) : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>From step</TableHead>
                            <TableHead>To step</TableHead>
                            <TableHead className="w-32">Minutes</TableHead>
                            {canDelete && <TableHead className="w-12"><span className="sr-only">Remove</span></TableHead>}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((r) => (
                            <TableRow key={r.id}>
                                <TableCell>{r.from_step_name}</TableCell>
                                <TableCell>{r.to_step_name}</TableCell>
                                <TableCell><MinutesCell row={r} canChange={canChange} /></TableCell>
                                {canDelete && (
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="icon" className="text-destructive"
                                            aria-label={`Remove ${r.from_step_name} to ${r.to_step_name}`}
                                            onClick={() => del.mutate(r.id, { onError: (e) => toastApiError(e) })}>
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
                <div className="grid gap-3 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_7rem_auto] sm:items-end">
                    <div className="space-y-1.5">
                        <Label>From step</Label>
                        <StepSelect value={fromStep} onChange={setFromStep} placeholder="Step it was running" />
                    </div>
                    <div className="space-y-1.5">
                        <Label>To step</Label>
                        <StepSelect value={toStep} onChange={setToStep} placeholder="Step it switches to" />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor={`co-min-${equipmentId}`}>Minutes</Label>
                        <Input id={`co-min-${equipmentId}`} type="number" min={0} step="any" inputMode="decimal"
                            value={minutes} onChange={(e) => setMinutes(e.target.value)} />
                    </div>
                    <Button size="sm" className="h-9" onClick={add} disabled={!fromStep || !toStep || create.isPending}>
                        <Plus className="mr-1 h-4 w-4" /> Add
                    </Button>
                </div>
            )}
        </div>
    );
}
