/**
 * "Subscribe to event" — the lightest-tier rule creation surface.
 *
 * For a casual user (QA inspector, operator) who just wants to be pinged on
 * a specific kind of event. No scope picker (always personal), no recipient
 * picker (always you), no nested groups, no CEL.
 *
 *   [Event ▾]
 *   When... (optional smart-token chips for the chosen event)
 *   Channels: ☑ In-app  ☑ Email
 *   [Subscribe]
 *
 * Saves a personal `NotificationRule` via the per-scope API. Coverage UI
 * is rendered but Phase 4 — not yet persisted; backend doesn't model
 * escalation yet.
 */
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

import { DelayInput } from "@/components/notifications/DelayInput";
import {
    SmartTokenIcon,
    SmartTokenRow,
} from "@/components/notifications/SmartTokenRow";

import {
    useCreatePersonalRule,
    useUpdatePersonalRule,
    type PersonalRule,
} from "@/hooks/notificationRules";
import { useRetrieveUsers } from "@/hooks/useRetrieveUsers";
import { useTenantGroups } from "@/hooks/useTenantGroups";

import {
    useNotificationEventCatalog,
} from "@/lib/notifications/eventCatalog";
import { getPayloadFields } from "@/lib/notifications/payloadSchemas";
import {
    emptyEscalation,
    newEscalationStepId,
    type EscalationPolicyDraft,
    type EscalationStepDraft,
} from "@/lib/notifications/ruleDraft";
import {
    defaultSmartTokenInstance,
    parseCelToRoot,
    rootToCel,
    rootToEnglish,
    SMART_TOKENS,
    type ConditionGroup,
    type ConditionNode,
    type EnglishPart,
    type SmartTokenDef,
    type SmartTokenInstance,
} from "@/lib/notifications/simpleConditions";

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** Existing personal rule to edit; null = creating a new subscription. */
    editingRule?: PersonalRule | null;
}

function isSmartToken(node: ConditionNode): node is SmartTokenInstance {
    return node.kind === "smart-token";
}

function channelsToList(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((c): c is string => typeof c === "string")
        : [];
}

export function SubscribeToEventSheet({ open, onOpenChange, editingRule = null }: Props) {
    const [eventCode, setEventCode] = useState<string>(
        editingRule?.event_code ?? "ncr.opened",
    );
    const [tokens, setTokens] = useState<SmartTokenInstance[]>([]);
    const [name, setName] = useState<string>(editingRule?.name ?? "");
    const [channels, setChannels] = useState<string[]>(
        channelsToList(editingRule?.channels) || ["in_app"],
    );
    const [coverage, setCoverage] = useState<EscalationPolicyDraft>(emptyEscalation());

    const createRule = useCreatePersonalRule();
    const updateRule = useUpdatePersonalRule();
    const saving = createRule.isPending || updateRule.isPending;

    // Reset state when the sheet opens or the editing target changes.
    useEffect(() => {
        if (!open) return;
        if (editingRule) {
            setEventCode(editingRule.event_code ?? "ncr.opened");
            setName(editingRule.name);
            setChannels(channelsToList(editingRule.channels));
            setCoverage(emptyEscalation()); // backend doesn't persist escalation yet
            // Round-trip existing CEL through the parser, keeping only the
            // smart-token children. Anything the parser can't recognize as
            // a token (custom CEL, leaf conditions) is silently dropped —
            // power users edit those in the full editor's Advanced mode.
            const parsed = parseCelToRoot(
                editingRule.conditions_source ?? "",
                getPayloadFields(editingRule.event_code ?? ""),
            );
            const recovered = parsed?.children.filter(isSmartToken) ?? [];
            setTokens(recovered);
        } else {
            setEventCode("ncr.opened");
            setName("");
            setChannels(["in_app"]);
            setTokens([]);
            setCoverage(emptyEscalation());
        }
    }, [open, editingRule]);

    // Authoritative gate from the backend ack registry, surfaced via the
    // events catalog. See `EscalationCard.tsx` for the same pattern.
    const coverageSupported = Boolean(
        catalogEvents.find((e) => e.code === eventCode)?.supportsEscalation,
    );

    const fields = useMemo(() => getPayloadFields(eventCode), [eventCode]);
    const applicableTokens = useMemo(
        () => SMART_TOKENS.filter((t) => t.appliesTo(fields)),
        [fields],
    );
    const {events: catalogEvents} = useNotificationEventCatalog();
    const event = catalogEvents.find((e) => e.code === eventCode);

    // Build a synthetic root group from the selected tokens to drive the
    // English readback and CEL emission. Tokens are joined with AND.
    const synthRoot = useMemo<ConditionGroup>(
        () => ({
            id: "root-synth",
            kind: "group",
            conjunction: "and",
            children: tokens,
        }),
        [tokens],
    );

    const englishParts = useMemo(
        () => rootToEnglish(synthRoot, fields),
        [synthRoot, fields],
    );

    const toggleChannel = (code: string, on: boolean) => {
        setChannels((curr) =>
            on ? [...new Set([...curr, code])] : curr.filter((c) => c !== code),
        );
    };

    const addToken = (def: SmartTokenDef) => {
        setTokens((prev) => [...prev, defaultSmartTokenInstance(def)]);
    };
    const removeToken = (id: string) => {
        setTokens((prev) => prev.filter((t) => t.id !== id));
    };
    const updateTokenParam = (
        id: string,
        params: Record<string, string | number>,
    ) => {
        setTokens((prev) => prev.map((t) => (t.id === id ? { ...t, params } : t)));
    };

    const handleSave = () => {
        const conditionsSource = rootToCel(synthRoot, fields);
        const displayName = name.trim() || (event?.label ?? "Subscription");
        const close = () => onOpenChange(false);

        if (editingRule) {
            updateRule.mutate(
                {
                    id: editingRule.id,
                    data: {
                        name: displayName,
                        event_code: eventCode,
                        conditions_source: conditionsSource || undefined,
                        channels,
                    },
                },
                { onSuccess: close },
            );
        } else {
            createRule.mutate(
                {
                    name: displayName,
                    event_code: eventCode,
                    conditions_source: conditionsSource || undefined,
                    channels,
                    enabled: true,
                },
                { onSuccess: close },
            );
        }
    };

    const canSave = channels.length > 0 && !saving;

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>
                        {editingRule ? "Edit subscription" : "Subscribe to event"}
                    </SheetTitle>
                    <SheetDescription>
                        Get notified when something happens that matters to you.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-5 px-4">
                    <ReadbackBanner parts={englishParts} eventLabel={event?.label} />

                    <div className="space-y-2">
                        <Label>Event</Label>
                        <Select value={eventCode} onValueChange={setEventCode}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {catalogEvents.map((e) => (
                                    <SelectItem key={e.code} value={e.code}>
                                        {e.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {event && (
                            <p className="text-xs text-muted-foreground">{event.description}</p>
                        )}
                    </div>

                    {applicableTokens.length > 0 && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label>Only when… (optional)</Label>
                                {tokens.length > 0 && (
                                    <button
                                        type="button"
                                        onClick={() => setTokens([])}
                                        className="text-xs text-muted-foreground hover:text-foreground"
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>

                            <div className="flex flex-wrap gap-1.5">
                                {applicableTokens.map((def) => (
                                    <Button
                                        key={def.id}
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs"
                                        onClick={() => addToken(def)}
                                    >
                                        <SmartTokenIcon name={def.icon} className="h-3.5 w-3.5 mr-1" />
                                        {def.label.replace(/\{[^}]+\}/g, "…")}
                                    </Button>
                                ))}
                            </div>

                            {tokens.length > 0 && (
                                <ul className="space-y-2 pt-1">
                                    {tokens.map((tok) => (
                                        <li key={tok.id}>
                                            <SmartTokenRow
                                                token={tok}
                                                onUpdate={(p) => updateTokenParam(tok.id, p)}
                                                onRemove={() => removeToken(tok.id)}
                                            />
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label>Notify me via</Label>
                        <div className="flex flex-col gap-2.5">
                            <label className="flex items-center justify-between cursor-pointer">
                                <span className="text-sm">In-app inbox</span>
                                <Switch
                                    checked={channels.includes("in_app")}
                                    onCheckedChange={(v) => toggleChannel("in_app", v)}
                                />
                            </label>
                            <label className="flex items-center justify-between cursor-pointer">
                                <span className="text-sm">Email</span>
                                <Switch
                                    checked={channels.includes("email")}
                                    onCheckedChange={(v) => toggleChannel("email", v)}
                                />
                            </label>
                        </div>
                        {!canSave && !saving && (
                            <p className="text-xs text-amber-700 dark:text-amber-400">
                                Pick at least one channel.
                            </p>
                        )}
                    </div>

                    {coverageSupported && (
                        <CoverageSection policy={coverage} onChange={setCoverage} />
                    )}
                </div>

                <SheetFooter className="flex-row gap-2">
                    <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button className="flex-1" onClick={handleSave} disabled={!canSave}>
                        {editingRule ? "Save" : "Subscribe"}
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}

// ---------------------------------------------------------------------------
// Coverage — single-step "forward when away" UI
//
// Rendered but Phase 4. Backend doesn't persist escalation yet, so toggling
// this does nothing at save time. Kept visible so the surface is ready
// when Phase 4 lands.
// ---------------------------------------------------------------------------

function CoverageSection({
    policy,
    onChange,
}: {
    policy: EscalationPolicyDraft;
    onChange: (next: EscalationPolicyDraft) => void;
}) {
    const step: EscalationStepDraft = policy.steps[0] ?? {
        id: newEscalationStepId(),
        delaySeconds: 4 * 3600,
        recipientUserIds: [],
        recipientGroupIds: [],
        subjectOverride: "",
    };

    const toggle = (enabled: boolean) => {
        if (enabled) {
            onChange({ enabled: true, steps: policy.steps.length ? policy.steps : [step] });
        } else {
            onChange({ enabled: false, steps: policy.steps });
        }
    };

    const updateStep = (patch: Partial<EscalationStepDraft>) => {
        onChange({ enabled: policy.enabled, steps: [{ ...step, ...patch }] });
    };

    return (
        <div className="rounded-md border">
            <div className="flex items-center justify-between p-3">
                <div>
                    <Label className="flex items-center gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
                        Forward when away
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        If you don't acknowledge in time, send to a backup.
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-0.5 italic">
                        Phase 4 — preview only; not yet saved.
                    </p>
                </div>
                <Switch checked={policy.enabled} onCheckedChange={toggle} />
            </div>

            {policy.enabled && (
                <div className="border-t p-3 space-y-3 bg-muted/20">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm text-muted-foreground">After</span>
                        <DelayInput
                            seconds={step.delaySeconds}
                            onChange={(s) => updateStep({ delaySeconds: s })}
                        />
                        <span className="text-sm text-muted-foreground">
                            without acknowledgement
                        </span>
                    </div>

                    <div className="space-y-1.5">
                        <Label className="text-xs">Forward to</Label>
                        <SimpleRecipientPicker
                            userIds={step.recipientUserIds}
                            groupIds={step.recipientGroupIds}
                            onChange={(userIds, groupIds) =>
                                updateStep({
                                    recipientUserIds: userIds,
                                    recipientGroupIds: groupIds,
                                })
                            }
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

function SimpleRecipientPicker({
    userIds,
    groupIds,
    onChange,
}: {
    userIds: number[];
    groupIds: string[];
    onChange: (userIds: number[], groupIds: string[]) => void;
}) {
    const { data: usersResp } = useRetrieveUsers();
    const { data: groupsResp } = useTenantGroups();

    // Flatten users + groups into a single picker since at the tier-2 level
    // "forward to my backup" doesn't need separate columns.
    const items = useMemo(() => {
        const users = (usersResp?.results ?? []).map((u) => ({
            key: `u-${u.id}`,
            label: `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() || u.username,
            kind: "user" as const,
            id: u.id,
        }));
        const groups = (groupsResp?.results ?? []).map((g) => ({
            key: `g-${g.id}`,
            label: g.name,
            kind: "group" as const,
            id: String(g.id),
        }));
        return [...users, ...groups];
    }, [usersResp, groupsResp]);

    const selectedKeys = new Set<string>([
        ...userIds.map((id) => `u-${id}`),
        ...groupIds.map((id) => `g-${id}`),
    ]);

    const toggle = (key: string, kind: "user" | "group", id: number | string) => {
        if (selectedKeys.has(key)) {
            if (kind === "user") onChange(userIds.filter((x) => x !== id), groupIds);
            else onChange(userIds, groupIds.filter((x) => x !== id));
        } else {
            if (kind === "user") onChange([...userIds, id as number], groupIds);
            else onChange(userIds, [...groupIds, id as string]);
        }
    };

    return (
        <div className="flex flex-wrap gap-1.5">
            {items.map((item) => {
                const selected = selectedKeys.has(item.key);
                return (
                    <button
                        key={item.key}
                        type="button"
                        onClick={() => toggle(item.key, item.kind, item.id)}
                        className={cn(
                            "text-xs rounded-md border px-2 py-1.5 transition-colors",
                            selected
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-background hover:bg-muted",
                        )}
                    >
                        {item.kind === "group" && (
                            <span className="text-[10px] opacity-70 mr-1">group</span>
                        )}
                        {item.label}
                    </button>
                );
            })}
        </div>
    );
}

function ReadbackBanner({
    parts,
    eventLabel,
}: {
    parts: EnglishPart[];
    eventLabel: string | undefined;
}) {
    const isAlways = parts.length === 1 && parts[0].text === "always";
    return (
        <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm leading-relaxed">
            <span className="text-muted-foreground">
                {isAlways ? "Notify me on every " : "Notify me when "}
            </span>
            {!isAlways &&
                parts.map((p, i) => (
                    <span
                        key={i}
                        className={p.emphasis ? "font-medium text-foreground" : "text-muted-foreground"}
                    >
                        {p.text}
                    </span>
                ))}
            {eventLabel && (
                <>
                    {!isAlways && <span className="text-muted-foreground"> on </span>}
                    <span className="font-medium">{eventLabel}</span>
                    <span className="text-muted-foreground">{isAlways ? " event" : ""}.</span>
                </>
            )}
        </div>
    );
}
