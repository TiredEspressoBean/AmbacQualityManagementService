"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Wrench } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useFixturesList } from "@/hooks/useScheduling";
import { useRetrieveStep } from "@/hooks/useRetrieveStep";
import { useUpdateStep } from "@/hooks/useUpdateStep";

export interface StepToolingEditorProps {
    stepId: string;
    stepName: string;
    /** The draft the step is edited in: tooling is controlled content (10b). */
    processId?: string | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    readOnly?: boolean;
}

/** Flow-editor dialog for the pooled tooling a step needs (Steps.required_tooling): a
 *  shim kit, identical collet chucks, an NC program. Each running op ties up one of it.
 *  Numbered items (a die, a fixture with its own number) are machines, not here. */
export function StepToolingEditor({ stepId, stepName, processId, open, onOpenChange, readOnly = false }: StepToolingEditorProps) {
    const { data: step } = useRetrieveStep({ params: { id: stepId } }, { enabled: open });
    const { data: fixtures } = useFixturesList({ offset: 0, limit: 500, ordering: "name" });
    const update = useUpdateStep();
    const [selected, setSelected] = useState<Set<string>>(new Set());

    useEffect(() => {
        const ids = (step as { required_tooling?: string[] } | undefined)?.required_tooling ?? [];
        setSelected(new Set(ids.map(String)));
    }, [step]);

    const rows = (fixtures?.results ?? []).filter((f) => !f.archived);
    const toggle = (id: string, on: boolean) =>
        setSelected((s) => { const n = new Set(s); if (on) n.add(id); else n.delete(id); return n; });

    const save = () => update.mutate(
        { id: stepId, processId: processId ?? undefined, data: { required_tooling: [...selected] } },
        {
            onSuccess: () => { toast.success("Tooling saved"); onOpenChange(false); },
            onError: (e: unknown) => {
                const d = (e as { response?: { data?: { required_tooling?: string[]; detail?: string } } })?.response?.data;
                toast.error(d?.required_tooling?.[0] ?? d?.detail ?? "Couldn't save the tooling.");
            },
        });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Wrench className="h-5 w-5" />
                        Tooling this step needs — "{stepName}"
                    </DialogTitle>
                    <DialogDescription>
                        Reusable tooling each running operation ties up. The plan won't run more
                        at once than are available, and work doesn't start when none is usable.
                    </DialogDescription>
                </DialogHeader>
                {rows.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No tooling is set up yet (Tooling, under Data Management).</p>
                ) : (
                    <ul className="max-h-80 space-y-1 overflow-y-auto">
                        {rows.map((f) => (
                            <li key={f.id} className="flex items-center gap-3 rounded px-2 py-1.5 hover:bg-muted/50">
                                <Checkbox id={`tool-${f.id}`} checked={selected.has(String(f.id))} disabled={readOnly}
                                    onCheckedChange={(v) => toggle(String(f.id), v === true)} />
                                <label htmlFor={`tool-${f.id}`} className="flex-1 text-sm">
                                    {f.name}
                                    <span className="ml-2 text-xs text-muted-foreground">
                                        {f.kind?.toLowerCase()} · {f.capacity} available{f.equipment_type ? " (tracked)" : ""}
                                    </span>
                                </label>
                            </li>
                        ))}
                    </ul>
                )}
                {!readOnly && (
                    <DialogFooter>
                        <Button onClick={save} disabled={update.isPending}>
                            {update.isPending ? "Saving…" : "Save tooling"}
                        </Button>
                    </DialogFooter>
                )}
            </DialogContent>
        </Dialog>
    );
}
