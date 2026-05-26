import { useMemo } from "react";
import { AlertTriangle, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiPicker } from "@/components/ui/multi-picker";
import { Switch } from "@/components/ui/switch";

import { DelayInput } from "@/components/notifications/DelayInput";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import { ackCopyFor, useNotificationEventCatalog } from "@/lib/notifications/eventCatalog";
import {
    newEscalationStepId,
    type EscalationPolicyDraft,
    type EscalationStepDraft,
    type RuleDraft,
} from "@/lib/notifications/ruleDraft";

const MAX_ESCALATION_STEPS = 3;

/**
 * Edits the rule's escalation chain. Mutates `draft.escalation`; the parent
 * page serializes it through `escalationToWire()` in `ruleDraft.ts` into the
 * nested `escalation` field on the rule create/patch payload.
 */
export function EscalationCard({
    draft,
    patch,
}: {
    draft: RuleDraft;
    patch: (u: Partial<RuleDraft>) => void;
}) {
    // Authoritative escalation-support flag comes from the backend ack
    // registry via the events catalog; the frontend used to hardcode this
    // and drift was a silent-failure trap (UI enabled the toggle for events
    // the dispatcher would refuse to create instances for).
    const { events: catalogEvents } = useNotificationEventCatalog();
    const eventDescriptor = catalogEvents.find((e) => e.code === draft.eventCode);
    const supportsEscalation = Boolean(eventDescriptor?.supportsEscalation);
    const ackText = ackCopyFor(draft.eventCode);
    const isPersonal = draft.scope === "personal";
    const title = isPersonal ? "Coverage" : "Escalation";
    const description = isPersonal
        ? "Forward to someone else if you don't acknowledge in time — useful when you're out of office."
        : "Notify additional people if the source record stays unacknowledged after a delay.";

    const setPolicy = (policy: EscalationPolicyDraft) => patch({ escalation: policy });
    const setSteps = (steps: EscalationStepDraft[]) =>
        setPolicy({ ...draft.escalation, steps });

    const addStep = () => {
        if (draft.escalation.steps.length >= MAX_ESCALATION_STEPS) return;
        setSteps([
            ...draft.escalation.steps,
            {
                id: newEscalationStepId(),
                delaySeconds: 4 * 3600,
                recipientUserIds: [],
                recipientGroupIds: [],
                subjectOverride: "",
            },
        ]);
    };

    const removeStep = (id: string) => {
        setSteps(draft.escalation.steps.filter((s) => s.id !== id));
    };

    const updateStep = (id: string, patchStep: Partial<EscalationStepDraft>) => {
        setSteps(
            draft.escalation.steps.map((s) => (s.id === id ? { ...s, ...patchStep } : s)),
        );
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <CardTitle className="text-base flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                            {title}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground mt-1">{description}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <Switch
                            checked={draft.escalation.enabled}
                            onCheckedChange={(v) =>
                                setPolicy({ ...draft.escalation, enabled: v })
                            }
                            disabled={!supportsEscalation}
                            aria-label="Enable escalation"
                        />
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {!supportsEscalation ? (
                    <div className="rounded-md border border-dashed px-3 py-4 text-xs text-muted-foreground">
                        Escalation isn't supported for this event yet — the backend needs
                        an "acknowledged" definition before the chain can know when to stop.
                    </div>
                ) : !draft.escalation.enabled ? (
                    <p className="text-xs text-muted-foreground">
                        {isPersonal
                            ? "Off. Turn on to forward to a backup when you're away."
                            : "Off. Turn on to add timed follow-up notifications."}
                    </p>
                ) : (
                    <div className="space-y-3">
                        {draft.escalation.steps.length === 0 ? (
                            <div className="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground">
                                No steps yet. Add the first follow-up below.
                            </div>
                        ) : (
                            <ol className="space-y-3">
                                {draft.escalation.steps.map((step, i) => (
                                    <EscalationStepRow
                                        key={step.id}
                                        index={i}
                                        step={step}
                                        onChange={(p) => updateStep(step.id, p)}
                                        onRemove={() => removeStep(step.id)}
                                    />
                                ))}
                            </ol>
                        )}

                        {draft.escalation.steps.length < MAX_ESCALATION_STEPS && (
                            <Button variant="outline" size="sm" onClick={addStep}>
                                <Plus className="h-3.5 w-3.5 mr-1.5" />
                                Add step
                            </Button>
                        )}

                        <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                            Stops escalating when{" "}
                            <span className="font-medium text-foreground">{ackText}</span>.
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function EscalationStepRow({
    index,
    step,
    onChange,
    onRemove,
}: {
    index: number;
    step: EscalationStepDraft;
    onChange: (p: Partial<EscalationStepDraft>) => void;
    onRemove: () => void;
}) {
    const { data: groupsResp } = useTenantGroups();
    const { data: usersResp } = useRetrieveUsers();

    const groupItems = useMemo(
        () =>
            (groupsResp?.results ?? []).map((g) => ({
                id: String(g.id),
                label: g.name,
            })),
        [groupsResp],
    );
    const userItems = useMemo(
        () =>
            (usersResp?.results ?? []).map((u) => ({
                id: u.id,
                label: `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.username,
            })),
        [usersResp],
    );

    return (
        <li className="rounded-md border bg-background p-3 space-y-3">
            <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Step {index + 1}
                </span>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={onRemove}
                    aria-label={`Remove step ${index + 1}`}
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted-foreground">After</span>
                <DelayInput
                    seconds={step.delaySeconds}
                    onChange={(s) => onChange({ delaySeconds: s })}
                />
                <span className="text-sm text-muted-foreground">
                    {index === 0 ? "from initial fire" : "after previous step"}
                </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <MultiPicker
                    label="Groups"
                    items={groupItems}
                    selected={step.recipientGroupIds}
                    onChange={(ids) => onChange({ recipientGroupIds: ids })}
                />
                <MultiPicker
                    label="Users"
                    items={userItems}
                    selected={step.recipientUserIds}
                    onChange={(ids) => onChange({ recipientUserIds: ids })}
                />
            </div>

            <div className="space-y-1">
                <Label className="text-xs">Subject override (optional)</Label>
                <Input
                    value={step.subjectOverride}
                    onChange={(e) => onChange({ subjectOverride: e.target.value })}
                    placeholder="e.g. URGENT — unacknowledged for 4 hours"
                    className="h-8 text-sm"
                />
            </div>
        </li>
    );
}
