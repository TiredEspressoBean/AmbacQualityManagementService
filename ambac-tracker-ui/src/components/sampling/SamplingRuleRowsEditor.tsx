"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RULE_TYPES } from "@/components/sampling/rule-types";
import { ruleSetRuleHistoryOptions } from "@/components/sampling/RuleSetRuleHistory";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { useRetrieveSamplingRules } from "@/hooks/useRetrieveSamplingRules";
import { useCreateSamplingRule } from "@/hooks/useCreateSamplingRule";
import { api } from "@/lib/api/generated";
import { useUpdateSamplingRule } from "@/hooks/useUpdateSamplingRule";
import { useDeleteSamplingRule } from "@/hooks/useDeleteSamplingRule";

const labelFor = (t: string) => RULE_TYPES.find((r) => r.value === t)?.label ?? t;
const unitFor = (t: string) => RULE_TYPES.find((r) => r.value === t)?.unit ?? "";
const needsValue = (t: string) => unitFor(t) !== "";

/** In-place CRUD of the rule rows (SamplingRule children) for one rule set.
 *  Each mutation persists immediately via the SamplingRule endpoint — separate
 *  from the ruleset header form's save. */
export function SamplingRuleRowsEditor({ rulesetId }: { rulesetId: string }) {
    const { data, refetch, isLoading } = useRetrieveSamplingRules({ ruleset: rulesetId });
    const queryClient = useQueryClient();
    // Refresh the set's "Rule changes" with every add / edit / remove.
    const refresh = () => {
        refetch();
        queryClient.invalidateQueries(ruleSetRuleHistoryOptions(rulesetId));
    };
    const create = useCreateSamplingRule();
    const update = useUpdateSamplingRule();
    const del = useDeleteSamplingRule();

    const rows = (((data as { results?: any[] })?.results) ?? [])
        .slice()
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

    // The contract's enum rather than a bare string, so the dropdown can only
    // offer rule types the endpoint accepts.
    type RuleType = Parameters<typeof api.api_Sampling_rules_create>[0]["rule_type"];
    const [newType, setNewType] = useState<RuleType>("EVERY_NTH_PART");
    const [newValue, setNewValue] = useState("");

    const add = async () => {
        try {
            await create.mutateAsync({
                ruleset: rulesetId,
                rule_type: newType,
                value: needsValue(newType) && newValue !== "" ? Number(newValue) : null,
                order: rows.length + 1,
            });
            setNewValue("");
            toast.success("Rule added");
            refresh();
        } catch {
            toast.error("Failed to add rule");
        }
    };

    // The last value sent per rule: a second blur before the refetch lands compared
    // against the stale value and sent the same PATCH again (two audit entries).
    const lastSent = useRef<Record<string, string>>({});
    const saveValue = async (id: string, v: string) => {
        if (lastSent.current[id] === v) return;
        lastSent.current[id] = v;
        try {
            await update.mutateAsync({ id, data: { value: v === "" ? null : Number(v) } });
            // The plan changed and is live now: say so (it saved silently).
            toast.success("Sampling rule updated — applies to parts from now on");
            refresh();
        } catch {
            delete lastSent.current[id];
            toast.error("Failed to update rule");
        }
    };

    const remove = async (id: string) => {
        try {
            await del.mutateAsync(id);
            toast.success("Rule removed");
            refresh();
        } catch {
            toast.error("Failed to remove rule");
        }
    };

    return (
        <div className="space-y-3">
            {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading rules…</p>
            ) : rows.length === 0 ? (
                <p className="text-sm text-muted-foreground">No rules yet — add one below.</p>
            ) : (
                <div className="space-y-2">
                    {rows.map((r) => (
                        <div key={r.id} className="flex items-center gap-3 rounded-md border p-2">
                            <Badge variant="secondary" className="shrink-0">{labelFor(r.rule_type)}</Badge>
                            {needsValue(r.rule_type) ? (
                                <div className="flex items-center gap-1">
                                    <Input
                                        type="number"
                                        className="h-8 w-24"
                                        defaultValue={r.value ?? ""}
                                        onBlur={(e) => {
                                            if (String(e.target.value) !== String(r.value ?? "")) saveValue(String(r.id), e.target.value);
                                        }}
                                    />
                                    <span className="text-xs text-muted-foreground">{unitFor(r.rule_type)}</span>
                                </div>
                            ) : (
                                <span className="text-xs text-muted-foreground">no value (acceptance plan from header)</span>
                            )}
                            <span className="ml-auto text-xs text-muted-foreground">order {r.order ?? "—"}</span>
                            <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                                onClick={() => remove(String(r.id))}>
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                </div>
            )}

            <div className="flex items-end gap-2 rounded-md border border-dashed p-3">
                <div className="space-y-1.5">
                    <Label className="text-xs">Rule type</Label>
                    <Select value={newType} onValueChange={(v) => setNewType(v as RuleType)}>
                        <SelectTrigger className="w-56"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            {RULE_TYPES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                        </SelectContent>
                    </Select>
                </div>
                {needsValue(newType) && (
                    <div className="space-y-1.5">
                        <Label className="text-xs">Value ({unitFor(newType)})</Label>
                        <Input type="number" className="w-28" value={newValue} onChange={(e) => setNewValue(e.target.value)} />
                    </div>
                )}
                <Button type="button" variant="outline" onClick={add} disabled={create.isPending}>
                    <Plus className="h-4 w-4 mr-1" /> Add rule
                </Button>
            </div>
        </div>
    );
}
