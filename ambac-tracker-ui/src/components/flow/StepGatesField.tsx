/**
 * A step's gates: the checks that refuse or hold work at this step, composed by the
 * engineer (user decisions 2026-11-11). Every gate is composable; a new step starts
 * with the floor. Each gate's stage — before work starts, or when the part leaves —
 * and its escape are fixed by the server's registry (services/mes/gates.py); only a
 * gate's own settings are edited here.
 */
import { Plus, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useTenantGroups } from "@/hooks/useTenantGroups";

export type StepGate = {
    gate: string;
    order?: number;
    fpi_scope?: string | null;
    qa_assurance?: string | null;
    revisit_assignment?: string | null;
    revisit_role?: string | null;
};

type Stage = "START" | "RELEASE";

/** The gates a step can carry, in the order they're listed. Mirrors
 *  services/mes/step_gates.py (COMPOSABLE_GATES). */
export const GATE_CATALOG: { gate: string; stage: Stage; label: string; hint: string }[] = [
    { gate: "work_order_not_workable", stage: "START", label: "Work order workable",
      hint: "A held, cancelled or completed work order starts no work." },
    { gate: "deviation_expired", stage: "START", label: "Deviation in date",
      hint: "A temporary change past its end date starts no work until change control extends it." },
    { gate: "part_quarantined", stage: "START", label: "Part not quarantined",
      hint: "A quarantined part waits for its disposition." },
    { gate: "core_awaiting_authorisation", stage: "START", label: "Customer authorisation",
      hint: "A reman unit parked for the customer's answer isn't worked." },
    { gate: "training_not_authorized", stage: "START", label: "Operator trained",
      hint: "The operator holds the step's training; a supervisor can authorize past it." },
    { gate: "revisit_rule", stage: "START", label: "Repeat visits",
      hint: "Who may work a part that comes back to this step; a supervisor can authorize past it." },
    { gate: "substeps_incomplete", stage: "RELEASE", label: "Work instruction done",
      hint: "The work instruction's required substeps are complete." },
    { gate: "qualified_operator", stage: "RELEASE", label: "Qualified operator on record",
      hint: "Work that never passed a start check needs a qualified operator recorded." },
    { gate: "life_limit", stage: "RELEASE", label: "Life limit",
      hint: "A part past its life limit doesn't move on without an approved extension." },
    { gate: "quarantine_hold", stage: "RELEASE", label: "Quarantine hold",
      hint: "A quarantined part can't move on from this step until its quarantine is decided." },
    { gate: "qa_signoff", stage: "RELEASE", label: "QA sign-off",
      hint: "QA signs the step off before parts move on." },
    { gate: "first_piece", stage: "RELEASE", label: "First piece",
      hint: "The first piece is bought off before the rest move on." },
    { gate: "measurement_out_of_spec", stage: "RELEASE", label: "Readings in spec",
      hint: "A part with an out-of-spec reading at this step can't move on until it's dealt with." },
];

/** A new step's default gates. Mirrors services/mes/step_gates.py (FLOOR_GATES). */
export const FLOOR_GATES = [
    "work_order_not_workable",
    "deviation_expired",
    "part_quarantined",
    "core_awaiting_authorisation",
    "training_not_authorized",
    "substeps_incomplete",
    "qualified_operator",
    "life_limit",
];

export const FPI_SCOPE_OPTIONS = [
    { value: "PER_WORKORDER", label: "Per work order" },
    { value: "PER_SHIFT", label: "Per shift" },
    { value: "PER_EQUIPMENT", label: "Per machine" },
];

/** What one passed (or waived) first piece releases, per scope. */
const FPI_SCOPE_HINT: Record<string, string> = {
    PER_WORKORDER: "One first piece releases this step for the whole work order.",
    PER_SHIFT: "Each shift needs its own first piece on the work order: Day and Night on the same date are separate. The shift is whichever started most recently.",
    PER_EQUIPMENT: "Each machine needs its own first piece on the work order. A part with no machine recorded is held.",
};

const QA_ASSURANCE_OPTIONS = [
    { value: "NONE", label: "Check off — recorded under their login" },
    { value: "PASSWORD", label: "Signature + password — they re-enter their own password" },
];

const REVISIT_OPTIONS = [
    { value: "SAME", label: "The same operator as before" },
    { value: "DIFFERENT", label: "A different operator" },
    { value: "ROLE", label: "Someone in a role" },
];

const STAGE_LABEL: Record<Stage, string> = { START: "Before start", RELEASE: "To move on" };

function defaultsFor(gate: string): StepGate {
    if (gate === "first_piece") return { gate, fpi_scope: "PER_WORKORDER", qa_assurance: "NONE" };
    if (gate === "qa_signoff") return { gate, qa_assurance: "NONE" };
    if (gate === "revisit_rule") return { gate, revisit_assignment: "DIFFERENT", revisit_role: null };
    return { gate };
}

function ordered(gates: StepGate[]): StepGate[] {
    const rank = new Map(GATE_CATALOG.map((g, i) => [g.gate, i]));
    return [...gates]
        .sort((a, b) => (rank.get(a.gate) ?? 99) - (rank.get(b.gate) ?? 99))
        .map((g, i) => ({ ...g, order: i }));
}

export function StepGatesField({
    gates,
    editable,
    onChange,
}: {
    gates: StepGate[];
    editable: boolean;
    onChange: (gates: StepGate[]) => void;
}) {
    const present = new Set(gates.map((g) => g.gate));
    const missing = GATE_CATALOG.filter((c) => !present.has(c.gate));
    const needsRoles = gates.some((g) => g.gate === "revisit_rule" && g.revisit_assignment === "ROLE");
    const { data: groupsResp } = useTenantGroups(undefined, undefined, { enabled: needsRoles });
    const groups = (groupsResp?.results ?? []) as Array<{ id: string; name: string }>;

    const update = (gate: string, patch: Partial<StepGate>) =>
        onChange(ordered(gates.map((g) => (g.gate === gate ? { ...g, ...patch } : g))));
    const remove = (gate: string) => onChange(ordered(gates.filter((g) => g.gate !== gate)));
    const add = (gate: string) => onChange(ordered([...gates, defaultsFor(gate)]));

    return (
        <div className="space-y-2">
            <Label className="text-sm font-normal">Gates</Label>
            <p className="text-xs text-muted-foreground">
                The checks that stop work starting at this step, or hold a part here until
                they're met.
            </p>
            <ul className="space-y-2">
                {ordered(gates).map((g) => {
                    const meta = GATE_CATALOG.find((c) => c.gate === g.gate);
                    return (
                        <li key={g.gate} className="rounded-md border p-2 space-y-1.5">
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">{meta?.label ?? g.gate}</span>
                                {meta && (
                                    <Badge variant="outline" className="text-[10px]">
                                        {STAGE_LABEL[meta.stage]}
                                    </Badge>
                                )}
                                {editable && (
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="ml-auto h-6 w-6"
                                        aria-label={`Remove ${meta?.label ?? g.gate}`}
                                        onClick={() => remove(g.gate)}
                                    >
                                        <X className="h-3.5 w-3.5" />
                                    </Button>
                                )}
                            </div>
                            {meta && <p className="text-xs text-muted-foreground">{meta.hint}</p>}

                            {g.gate === "first_piece" && (
                                <>
                                    <GateSetting
                                        label="First piece covers"
                                        value={g.fpi_scope || "PER_WORKORDER"}
                                        options={FPI_SCOPE_OPTIONS}
                                        editable={editable}
                                        onChange={(v) => update(g.gate, { fpi_scope: v })}
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        {FPI_SCOPE_HINT[g.fpi_scope || "PER_WORKORDER"]}
                                    </p>
                                    {/* The buy-off is a QA release of its own: signed as
                                        the author sets here (or as the QA sign-off asks, if
                                        that asks for more). */}
                                    <GateSetting
                                        label="How the inspector signs the buy-off"
                                        value={g.qa_assurance ?? "NONE"}
                                        options={QA_ASSURANCE_OPTIONS}
                                        editable={editable}
                                        onChange={(v) => update(g.gate, { qa_assurance: v })}
                                    />
                                </>
                            )}
                            {g.gate === "qa_signoff" && (
                                <GateSetting
                                    label="How the inspector signs"
                                    value={g.qa_assurance ?? "NONE"}
                                    options={QA_ASSURANCE_OPTIONS}
                                    editable={editable}
                                    onChange={(v) => update(g.gate, { qa_assurance: v })}
                                />
                            )}
                            {g.gate === "revisit_rule" && (
                                <>
                                    <GateSetting
                                        label="Repeat visits are worked by"
                                        value={g.revisit_assignment ?? "DIFFERENT"}
                                        options={REVISIT_OPTIONS}
                                        editable={editable}
                                        onChange={(v) => update(g.gate, {
                                            revisit_assignment: v,
                                            ...(v === "ROLE" ? {} : { revisit_role: null }),
                                        })}
                                    />
                                    {g.revisit_assignment === "ROLE" && (
                                        <GateSetting
                                            label="Role"
                                            value={g.revisit_role ?? ""}
                                            options={groups.map((r) => ({ value: r.id, label: r.name }))}
                                            placeholder="Pick a role"
                                            editable={editable}
                                            onChange={(v) => update(g.gate, { revisit_role: v || null })}
                                        />
                                    )}
                                </>
                            )}
                        </li>
                    );
                })}
            </ul>
            {editable && missing.length > 0 && (
                <Select value="" onValueChange={(v) => v && add(v)}>
                    <SelectTrigger aria-label="Add a gate" className="h-8">
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Plus className="h-3.5 w-3.5" /> Add a gate
                        </span>
                    </SelectTrigger>
                    <SelectContent>
                        {missing.map((c) => (
                            <SelectItem key={c.gate} value={c.gate}>
                                {c.label} — {STAGE_LABEL[c.stage].toLowerCase()}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            )}
        </div>
    );
}

function GateSetting({
    label, value, options, editable, onChange, placeholder,
}: {
    label: string;
    value: string;
    options: { value: string; label: string }[];
    editable: boolean;
    onChange: (v: string) => void;
    placeholder?: string;
}) {
    if (!editable) {
        return (
            <p className="text-xs">
                {label}: {options.find((o) => o.value === value)?.label ?? (value || "—")}
            </p>
        );
    }
    return (
        <div className="space-y-1">
            <Label className="text-xs font-normal text-muted-foreground">{label}</Label>
            <Select value={value} onValueChange={(v) => v && onChange(v)}>
                <SelectTrigger className="h-8" aria-label={label}>
                    <SelectValue placeholder={placeholder} />
                </SelectTrigger>
                <SelectContent>
                    {options.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}
