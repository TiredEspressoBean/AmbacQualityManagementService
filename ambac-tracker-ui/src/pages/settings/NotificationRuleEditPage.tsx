/**
 * Phase 3 notification rules — full-page editor.
 *
 * Composes per-card sub-components from `components/notifications/rule-editor/`.
 * Owns local draft state, simple/advanced condition mode, scope-aware
 * fetch/save dispatch.
 *
 * Routed at:
 *   /settings/notification-rules/new?scope=tenant|customer|personal
 *   /settings/notification-rules/$ruleId/edit?scope=tenant|customer|personal
 *
 * The `scope` search param on the edit route tells us which per-scope
 * endpoint to fetch from. The list page stamps it when navigating to edit.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, FlaskConical, Save, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { BasicsCard } from "@/components/notifications/rule-editor/BasicsCard";
import { DeliveryCard } from "@/components/notifications/rule-editor/DeliveryCard";
import { EscalationCard } from "@/components/notifications/rule-editor/EscalationCard";
import { RecipientsCard } from "@/components/notifications/rule-editor/RecipientsCard";
import { ScopeCard } from "@/components/notifications/rule-editor/ScopeCard";
import { TestRuleSheet } from "@/components/notifications/rule-editor/TestRuleSheet";
import {
    TriggerCard,
    type EditorMode,
} from "@/components/notifications/rule-editor/TriggerCard";

import {
    useCreateCustomerRule,
    useCreatePersonalRule,
    useCreateTenantRule,
    useDeleteCustomerRule,
    useDeletePersonalRule,
    useDeleteTenantRule,
    useRetrieveCustomerRule,
    useRetrievePersonalRule,
    useRetrieveTenantRule,
    useUpdateCustomerRule,
    useUpdatePersonalRule,
    useUpdateTenantRule,
} from "@/hooks/notificationRules";

import { useNotificationEventCatalog } from "@/lib/notifications/eventCatalog";
import { getPayloadFields } from "@/lib/notifications/payloadSchemas";
import {
    emptyRootGroup,
    parseCelToRoot,
    rootToCel,
    rootToEnglish,
    type ConditionGroup,
    type EnglishPart,
} from "@/lib/notifications/simpleConditions";
import {
    blankRuleDraft,
    customerRuleToDraft,
    draftToCustomerCreate,
    draftToCustomerPatch,
    draftToPersonalCreate,
    draftToPersonalPatch,
    draftToTenantCreate,
    draftToTenantPatch,
    personalRuleToDraft,
    SCOPE_LABELS,
    tenantRuleToDraft,
    type RuleDraft,
    type RuleScope,
} from "@/lib/notifications/ruleDraft";

export function NotificationRuleEditPage({
    ruleId,
    initialScope,
}: {
    ruleId?: string;
    /** Required by the route — scope is a structural path param, not a
     * filter. Drives both the initial draft shape for new rules and which
     * per-scope retrieve endpoint to fetch from on edit. */
    initialScope: RuleScope;
}) {
    const isNew = !ruleId;

    // Single retrieve query against the correct endpoint. `enabled` gates by
    // scope so React's rules-of-hooks invariant holds (always call all three),
    // but at most one fires.
    const tenantQ = useRetrieveTenantRule(ruleId ?? "", {
        enabled: !isNew && initialScope === "tenant",
    });
    const customerQ = useRetrieveCustomerRule(ruleId ?? "", {
        enabled: !isNew && initialScope === "customer",
    });
    const personalQ = useRetrievePersonalRule(ruleId ?? "", {
        enabled: !isNew && initialScope === "personal",
    });

    const activeQ =
        initialScope === "tenant"
            ? tenantQ
            : initialScope === "customer"
              ? customerQ
              : personalQ;

    const loadedDraft = useMemo<RuleDraft | null>(() => {
        if (isNew) return null;
        if (initialScope === "tenant" && tenantQ.data) return tenantRuleToDraft(tenantQ.data);
        if (initialScope === "customer" && customerQ.data) return customerRuleToDraft(customerQ.data);
        if (initialScope === "personal" && personalQ.data) return personalRuleToDraft(personalQ.data);
        return null;
    }, [isNew, initialScope, tenantQ.data, customerQ.data, personalQ.data]);

    if (!isNew && !loadedDraft && !activeQ.isPending) {
        return (
            <div className="container mx-auto p-6 max-w-7xl">
                <p className="text-sm text-muted-foreground">Rule not found.</p>
            </div>
        );
    }

    if (isNew || loadedDraft) {
        return (
            <EditorBody
                key={loadedDraft?.id ?? "new"}
                initialDraft={loadedDraft ?? blankRuleDraft(initialScope)}
                isNew={isNew}
            />
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <p className="text-sm text-muted-foreground">Loading rule…</p>
        </div>
    );
}

// =============================================================================
// EditorBody — mounted once we have the initial draft. Owns the form state.
// =============================================================================

function EditorBody({
    initialDraft,
    isNew,
}: {
    initialDraft: RuleDraft;
    isNew: boolean;
}) {
    const navigate = useNavigate();
    const [draft, setDraft] = useState<RuleDraft>(initialDraft);
    const patch = (updates: Partial<RuleDraft>) =>
        setDraft((current) => ({ ...current, ...updates }));

    const { events: catalogEvents } = useNotificationEventCatalog();
    const event = catalogEvents.find((e) => e.code === draft.eventCode);
    const fields = getPayloadFields(draft.eventCode);

    // Simple / advanced condition mode + tree state. Parse on mount; anything
    // outside the supported subset forces Advanced.
    const initialParse = useMemo(
        () => parseCelToRoot(initialDraft.conditionsSource, fields),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [],
    );
    const [mode, setMode] = useState<EditorMode>(initialParse ? "simple" : "advanced");
    const [root, setRoot] = useState<ConditionGroup>(initialParse ?? emptyRootGroup());

    // When the event changes, prune leaves that reference fields the new
    // payload doesn't expose.
    useEffect(() => {
        if (mode !== "simple") return;
        const validFieldNames = new Set(fields.map((f) => f.name));
        const filtered = filterRoot(root, validFieldNames);
        if (filtered !== root) setRoot(filtered);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [draft.eventCode]);

    // In simple mode, regenerate canonical CEL whenever the tree changes.
    useEffect(() => {
        if (mode !== "simple") return;
        const generated = rootToCel(root, fields);
        if (generated !== draft.conditionsSource) {
            patch({ conditionsSource: generated });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [root, mode, draft.eventCode]);

    const switchToSimple = () => {
        const parsed = parseCelToRoot(draft.conditionsSource, fields);
        if (!parsed) {
            const proceed = window.confirm(
                "Your condition uses syntax the form builder can't represent. " +
                    "Switching will discard the current condition. Proceed?",
            );
            if (!proceed) return;
            setRoot(emptyRootGroup());
            patch({ conditionsSource: "" });
        } else {
            setRoot(parsed);
        }
        setMode("simple");
    };
    const switchToAdvanced = () => setMode("advanced");

    const englishParts = useMemo(
        () => (mode === "simple" ? rootToEnglish(root, fields) : null),
        [mode, root, fields],
    );

    const close = () => navigate({ to: "/settings/notification-rules" });

    // Scope-aware save/delete dispatch.
    const createTenant = useCreateTenantRule();
    const createCustomer = useCreateCustomerRule();
    const createPersonal = useCreatePersonalRule();
    const updateTenant = useUpdateTenantRule();
    const updateCustomer = useUpdateCustomerRule();
    const updatePersonal = useUpdatePersonalRule();
    const deleteTenant = useDeleteTenantRule();
    const deleteCustomer = useDeleteCustomerRule();
    const deletePersonal = useDeletePersonalRule();

    const saving =
        createTenant.isPending ||
        createCustomer.isPending ||
        createPersonal.isPending ||
        updateTenant.isPending ||
        updateCustomer.isPending ||
        updatePersonal.isPending;

    const save = () => {
        if (isNew) {
            const onSettled = () => close();
            if (draft.scope === "tenant")
                createTenant.mutate(draftToTenantCreate(draft), { onSuccess: onSettled });
            else if (draft.scope === "customer")
                createCustomer.mutate(draftToCustomerCreate(draft), { onSuccess: onSettled });
            else createPersonal.mutate(draftToPersonalCreate(draft), { onSuccess: onSettled });
        } else {
            const onSettled = () => close();
            if (draft.scope === "tenant")
                updateTenant.mutate(
                    { id: draft.id, data: draftToTenantPatch(draft) },
                    { onSuccess: onSettled },
                );
            else if (draft.scope === "customer")
                updateCustomer.mutate(
                    { id: draft.id, data: draftToCustomerPatch(draft) },
                    { onSuccess: onSettled },
                );
            else
                updatePersonal.mutate(
                    { id: draft.id, data: draftToPersonalPatch(draft) },
                    { onSuccess: onSettled },
                );
        }
    };

    const remove = () => {
        if (!draft.id) return;
        const onSettled = () => close();
        if (draft.scope === "tenant")
            deleteTenant.mutate(draft.id, { onSuccess: onSettled });
        else if (draft.scope === "customer")
            deleteCustomer.mutate(draft.id, { onSuccess: onSettled });
        else deletePersonal.mutate(draft.id, { onSuccess: onSettled });
    };

    const canSave = draft.name.trim().length > 0 && !saving &&
        (draft.scope !== "customer" || Boolean(draft.scopeCustomerId));
    const [testPanelOpen, setTestPanelOpen] = useState(false);

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="sticky top-0 z-10 -mx-6 px-6 pt-6 pb-4 mb-6 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b">
                <div className="flex items-center justify-between gap-4 mb-3">
                    <Link
                        to="/settings/notification-rules"
                        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        All rules
                    </Link>
                    <div className="flex items-center gap-2 shrink-0">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setTestPanelOpen(true)}
                        >
                            <FlaskConical className="h-4 w-4 mr-2" />
                            Test rule
                        </Button>
                        {!isNew && (
                            <Button variant="outline" size="sm" onClick={remove}>
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                            </Button>
                        )}
                        <Button variant="outline" size="sm" onClick={close}>
                            Cancel
                        </Button>
                        <Button size="sm" onClick={save} disabled={!canSave}>
                            <Save className="h-4 w-4 mr-2" />
                            {isNew ? "Create rule" : "Save changes"}
                        </Button>
                    </div>
                </div>
                <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                        {isNew ? "New rule" : "Edit rule"}
                    </span>
                    <Badge variant="secondary">{SCOPE_LABELS[draft.scope]}</Badge>
                </div>
                {mode === "simple" && englishParts ? (
                    <HeadlineReadback parts={englishParts} eventLabel={event?.label} />
                ) : (
                    <p className="text-xl font-semibold leading-tight">
                        {draft.name || "Untitled rule"}
                    </p>
                )}
            </div>

            <div className="space-y-6 max-w-4xl">
                <BasicsCard draft={draft} patch={patch} />
                <ScopeCard draft={draft} patch={patch} lockedScope={!isNew} />
                <TriggerCard
                    draft={draft}
                    patch={patch}
                    fields={fields}
                    mode={mode}
                    root={root}
                    setRoot={setRoot}
                    onSwitchToSimple={switchToSimple}
                    onSwitchToAdvanced={switchToAdvanced}
                />
                {draft.scope !== "personal" && (
                    <RecipientsCard draft={draft} patch={patch} />
                )}
                <DeliveryCard draft={draft} patch={patch} />
                <EscalationCard draft={draft} patch={patch} />
            </div>

            <TestRuleSheet
                open={testPanelOpen}
                onOpenChange={setTestPanelOpen}
                draft={draft}
            />
        </div>
    );
}

function HeadlineReadback({
    parts,
    eventLabel,
}: {
    parts: EnglishPart[];
    eventLabel: string | undefined;
}) {
    const isAlways = parts.length === 1 && parts[0].text === "always";
    return (
        <p className="text-xl font-semibold leading-snug tracking-tight">
            <span className="text-muted-foreground">
                {isAlways ? "Fires on every " : "Notify when "}
            </span>
            {!isAlways &&
                parts.map((p, i) => (
                    <span
                        key={i}
                        className={p.emphasis ? "text-foreground" : "text-muted-foreground"}
                    >
                        {p.text}
                    </span>
                ))}
            {eventLabel && (
                <>
                    <span className="text-muted-foreground">{isAlways ? " " : " on "}</span>
                    <span>{eventLabel}</span>
                    <span className="text-muted-foreground">{isAlways ? " event" : ""}.</span>
                </>
            )}
        </p>
    );
}

/**
 * Drop condition leaves that reference fields not present on the current
 * event. Smart tokens and groups are preserved.
 */
function filterRoot(root: ConditionGroup, validFieldNames: Set<string>): ConditionGroup {
    const filteredChildren = root.children
        .map((c) => {
            if (c.kind === "condition") {
                return validFieldNames.has(c.field) ? c : null;
            }
            if (c.kind === "group") {
                return filterRoot(c, validFieldNames);
            }
            return c;
        })
        .filter((c): c is NonNullable<typeof c> => c !== null);
    const allEqual =
        filteredChildren.length === root.children.length &&
        filteredChildren.every((c, i) => c === root.children[i]);
    if (allEqual) return root;
    return { ...root, children: filteredChildren };
}

export default NotificationRuleEditPage;
