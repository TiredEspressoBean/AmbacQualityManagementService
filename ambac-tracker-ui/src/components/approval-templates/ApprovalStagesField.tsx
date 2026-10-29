import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { RequiredApproversField } from "@/components/approval-templates/RequiredApproversField";

/** One stage of a sequential approval: named people and/or groups. */
export type ApprovalStage = { users: number[]; groups: string[] };

type Props = {
    value: ApprovalStage[];
    onChange: (next: ApprovalStage[]) => void;
    disabled?: boolean;
};

/**
 * The ordered stages of a SEQUENTIAL approval template (user decision 2026-10-29).
 *
 * Stage 1 answers first; a later stage can't approve or reject until every earlier
 * stage is done. Within a stage every named person must approve, and any one member of
 * each group. The order is stored on the template (`approval_stages`) and copied onto
 * each request when it's made, so editing here never re-orders one already in flight.
 */
export function ApprovalStagesField({ value, onChange, disabled }: Props) {
    const stages = value.length ? value : [{ users: [], groups: [] }];
    const set = (next: ApprovalStage[]) => onChange(next);
    const move = (i: number, d: -1 | 1) => {
        const next = [...stages];
        [next[i], next[i + d]] = [next[i + d], next[i]];
        set(next);
    };
    return (
        <div className="space-y-3">
            {stages.map((stage, i) => (
                <div key={i} className="rounded-md border p-3 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Stage {i + 1}</span>
                        <div className="flex items-center gap-1">
                            <Button type="button" variant="ghost" size="icon" className="h-7 w-7"
                                    disabled={disabled || i === 0} onClick={() => move(i, -1)} title="Move up">
                                <ArrowUp className="h-4 w-4" />
                            </Button>
                            <Button type="button" variant="ghost" size="icon" className="h-7 w-7"
                                    disabled={disabled || i === stages.length - 1} onClick={() => move(i, 1)} title="Move down">
                                <ArrowDown className="h-4 w-4" />
                            </Button>
                            <Button type="button" variant="ghost" size="icon" className="h-7 w-7"
                                    disabled={disabled || stages.length === 1}
                                    onClick={() => set(stages.filter((_, j) => j !== i))} title="Remove stage">
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                    <RequiredApproversField
                        value={{ approvers: stage.users, groups: stage.groups }}
                        onChange={(next) => set(stages.map((s, j) => j === i ? { users: next.approvers, groups: next.groups } : s))}
                        disabled={disabled}
                    />
                </div>
            ))}
            <Button type="button" variant="outline" size="sm" disabled={disabled}
                    onClick={() => set([...stages, { users: [], groups: [] }])}>
                <Plus className="mr-1 h-4 w-4" /> Add stage
            </Button>
            <p className="text-xs text-muted-foreground">
                Each stage answers in turn — a later stage can't approve or reject until every earlier
                one is done. Everyone named in a stage must approve; for a group, any one member.
                The auto-assign group, if set, is a final stage after these.
            </p>
        </div>
    );
}
