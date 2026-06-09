import { Badge } from "@/components/ui/badge";
import { Plus, Minus, Pencil } from "lucide-react";

type ScalarDiff = { from: unknown; to: unknown };

type StepEntry = {
    id: string;
    name?: string;
    step_type?: string;
    changes?: Record<string, ScalarDiff | { changed: true }>;
};

type EdgeEntry = { from_step: string; to_step: string; edge_type: string };

type SubstepEntry = {
    id: string;
    title?: string;
    order?: number;
    changes?: Record<string, ScalarDiff | { changed: true }>;
};

export type ProcessDiff = {
    from_process_id?: string;
    to_process_id?: string;
    from_version?: number | null;
    to_version?: number | null;
    process?: Record<string, ScalarDiff>;
    steps?: { added?: StepEntry[]; removed?: StepEntry[]; modified?: StepEntry[] };
    edges?: { added?: EdgeEntry[]; removed?: EdgeEntry[] };
    substeps?: Record<string, { added?: SubstepEntry[]; removed?: SubstepEntry[]; modified?: SubstepEntry[] }>;
};

const fmtVal = (v: unknown): string => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "true" : "false";
    return String(v);
};

const isEmpty = (diff: ProcessDiff): boolean => {
    if (diff.process && Object.keys(diff.process).length > 0) return false;
    if (diff.steps && (diff.steps.added?.length || diff.steps.removed?.length || diff.steps.modified?.length)) return false;
    if (diff.edges && (diff.edges.added?.length || diff.edges.removed?.length)) return false;
    if (diff.substeps && Object.values(diff.substeps).some(g => g.added?.length || g.removed?.length || g.modified?.length)) return false;
    return true;
};

function ChangesTable({ changes }: { changes: Record<string, ScalarDiff | { changed: true }> }) {
    return (
        <table className="text-sm w-full">
            <tbody>
                {Object.entries(changes).map(([field, change]) => (
                    <tr key={field} className="border-b last:border-0">
                        <td className="py-1 pr-3 font-mono text-xs text-muted-foreground">{field}</td>
                        <td className="py-1 pr-3">
                            {"changed" in change ? (
                                <Badge variant="outline" className="text-xs">modified</Badge>
                            ) : (
                                <>
                                    <span className="text-destructive line-through">{fmtVal(change.from)}</span>
                                    <span className="mx-2 text-muted-foreground">→</span>
                                    <span className="text-emerald-700 dark:text-emerald-400">{fmtVal(change.to)}</span>
                                </>
                            )}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

export function PcrDiffViewer({ diff }: { diff: ProcessDiff | null | undefined }) {
    if (!diff) {
        return (
            <div className="text-sm text-muted-foreground italic p-4">
                No diff captured. The PCR was submitted without a linked draft, or no
                changes were made to the draft.
            </div>
        );
    }

    if (isEmpty(diff)) {
        return (
            <div className="text-sm text-muted-foreground italic p-4">
                The draft is identical to the approved baseline — no changes detected.
            </div>
        );
    }

    const stepsAdded = diff.steps?.added ?? [];
    const stepsRemoved = diff.steps?.removed ?? [];
    const stepsModified = diff.steps?.modified ?? [];
    const edgesAdded = diff.edges?.added ?? [];
    const edgesRemoved = diff.edges?.removed ?? [];

    return (
        <div className="space-y-5">
            <div className="text-xs text-muted-foreground">
                Comparing version{" "}
                <span className="font-mono">{diff.from_version ?? "?"}</span> →{" "}
                <span className="font-mono">{diff.to_version ?? "?"}</span>
            </div>

            {diff.process && Object.keys(diff.process).length > 0 && (
                <section>
                    <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                        <Pencil className="h-3.5 w-3.5" /> Process fields
                    </h3>
                    <div className="border rounded-md p-3 bg-muted/30">
                        <ChangesTable changes={diff.process} />
                    </div>
                </section>
            )}

            {(stepsAdded.length > 0 || stepsRemoved.length > 0 || stepsModified.length > 0) && (
                <section>
                    <h3 className="text-sm font-semibold mb-2">Steps</h3>
                    <div className="space-y-2">
                        {stepsAdded.map(s => (
                            <div key={`add-${s.id}`} className="flex items-start gap-2 text-sm border-l-2 border-emerald-500 pl-3">
                                <Plus className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                                <div>
                                    <div className="font-medium">{s.name}</div>
                                    {s.step_type && <div className="text-xs text-muted-foreground">{s.step_type}</div>}
                                </div>
                            </div>
                        ))}
                        {stepsRemoved.map(s => (
                            <div key={`rem-${s.id}`} className="flex items-start gap-2 text-sm border-l-2 border-destructive pl-3">
                                <Minus className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                                <div>
                                    <div className="font-medium line-through">{s.name}</div>
                                    {s.step_type && <div className="text-xs text-muted-foreground">{s.step_type}</div>}
                                </div>
                            </div>
                        ))}
                        {stepsModified.map(s => (
                            <div key={`mod-${s.id}`} className="border-l-2 border-amber-500 pl-3">
                                <div className="flex items-start gap-2 text-sm">
                                    <Pencil className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                                    <div className="flex-1">
                                        <div className="font-medium">{s.name}</div>
                                        {s.changes && (
                                            <div className="mt-1">
                                                <ChangesTable changes={s.changes} />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {(edgesAdded.length > 0 || edgesRemoved.length > 0) && (
                <section>
                    <h3 className="text-sm font-semibold mb-2">Edges</h3>
                    <div className="space-y-1 font-mono text-xs">
                        {edgesAdded.map((e, i) => (
                            <div key={`ea-${i}`} className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                                <Plus className="h-3.5 w-3.5" />
                                {e.from_step.slice(0, 8)}… → {e.to_step.slice(0, 8)}… <span className="text-muted-foreground">({e.edge_type})</span>
                            </div>
                        ))}
                        {edgesRemoved.map((e, i) => (
                            <div key={`er-${i}`} className="flex items-center gap-2 text-destructive line-through">
                                <Minus className="h-3.5 w-3.5" />
                                {e.from_step.slice(0, 8)}… → {e.to_step.slice(0, 8)}… <span>({e.edge_type})</span>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {diff.substeps && Object.entries(diff.substeps).some(([, g]) => g.added?.length || g.removed?.length || g.modified?.length) && (
                <section>
                    <h3 className="text-sm font-semibold mb-2">Substeps</h3>
                    <div className="space-y-3">
                        {Object.entries(diff.substeps).map(([stepId, group]) => {
                            const added = group.added ?? [];
                            const removed = group.removed ?? [];
                            const modified = group.modified ?? [];
                            if (!added.length && !removed.length && !modified.length) return null;
                            return (
                                <div key={stepId} className="border rounded-md p-3 bg-muted/30">
                                    <div className="text-xs text-muted-foreground mb-2 font-mono">Step {stepId.slice(0, 8)}…</div>
                                    {added.map(s => (
                                        <div key={`sa-${s.id}`} className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                                            <Plus className="h-3.5 w-3.5" /> {s.title} <span className="text-xs text-muted-foreground">(order {s.order})</span>
                                        </div>
                                    ))}
                                    {removed.map(s => (
                                        <div key={`sr-${s.id}`} className="flex items-center gap-2 text-sm text-destructive line-through">
                                            <Minus className="h-3.5 w-3.5" /> {s.title}
                                        </div>
                                    ))}
                                    {modified.map(s => (
                                        <div key={`sm-${s.id}`} className="mt-2">
                                            <div className="flex items-center gap-2 text-sm">
                                                <Pencil className="h-3.5 w-3.5 text-amber-600" /> {s.title}
                                            </div>
                                            {s.changes && <div className="ml-5 mt-1"><ChangesTable changes={s.changes} /></div>}
                                        </div>
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}
        </div>
    );
}
