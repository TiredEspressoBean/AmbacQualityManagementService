/**
 * Editor-side draft type for notification rules and converters to/from the
 * three per-scope backend shapes.
 *
 * The backend has three serializers — TenantRule, CustomerRule, PersonalRule
 * — each exposing only the fields valid for its scope. The editor needs one
 * mutable shape it can keep coherent while the user toggles scope on a new
 * rule. This file is the single boundary between that UI shape and the
 * generated API types.
 *
 * Escalation is a nested object on each rule scope; the draft holds it as
 * `EscalationPolicyDraft` and the wire side serializes it as `_Escalation` /
 * `_EscalationRequest`.
 *
 * ID conventions:
 *   - User IDs are integers (Django auth User).
 *   - Group / customer / external-contact / rule IDs are UUID strings.
 *   - `channels` on the wire is `string[]` (e.g. ["email", "in_app"]); the
 *     editor mirrors that — no parallel boolean map.
 */
import type {
    CustomerRule,
    CustomerRuleRequest,
    PatchedCustomerRuleRequest,
    PatchedPersonalRuleRequest,
    PatchedTenantRuleRequest,
    PersonalRule,
    PersonalRuleRequest,
    TenantRule,
    TenantRuleRequest,
} from "@/hooks/notificationRules";
import type { _Escalation } from "@/lib/api/generated";

export type RuleScope = "tenant" | "customer" | "personal";

export const SCOPE_LABELS: Record<RuleScope, string> = {
    tenant: "Tenant-wide",
    customer: "Customer-scoped",
    personal: "Personal",
};

export interface EscalationStepDraft {
    id: string;
    delaySeconds: number;
    recipientUserIds: number[];
    recipientGroupIds: string[];
    subjectOverride: string;
}

export interface EscalationPolicyDraft {
    enabled: boolean;
    steps: EscalationStepDraft[];
}

/** Where the dispatcher pulls recipients from at fire time. See
 * `NotificationRule.recipient_strategy` on the backend. */
export type RecipientStrategy = "static" | "from_payload" | "union";

export interface RuleDraft {
    /** Empty string for a fresh draft. */
    id: string;
    scope: RuleScope;
    name: string;
    description: string;
    eventCode: string;
    conditionsSource: string;
    channels: string[];
    priority: number;
    enabled: boolean;
    minGapSeconds: number;
    /**
     * `static` (default): only the rule's recipient_users/groups/external.
     * `from_payload`: dispatcher reads `payload.recipient_user_ids` (etc.)
     *   at fire time — for per-instance routing where the recipient is a
     *   property of the source record, not the rule.
     * `union`: combines both — static recipients become CCs on top of
     *   domain-driven routing.
     */
    recipientStrategy: RecipientStrategy;
    recipientUserIds: number[];
    recipientGroupIds: string[];
    /** Customer scope only. Empty string if unset. */
    scopeCustomerId: string;
    recipientExternalIds: string[];
    /** Personal scope only. Read-only from backend (stamped from request user). */
    ownerUserId: number | null;
    escalation: EscalationPolicyDraft;
}

export function emptyEscalation(): EscalationPolicyDraft {
    return { enabled: false, steps: [] };
}

export function newEscalationStepId(): string {
    return `es-${Math.random().toString(36).slice(2, 9)}`;
}

function escalationFromWire(
    e: _Escalation | null | undefined,
): EscalationPolicyDraft {
    if (!e) return emptyEscalation();
    return {
        enabled: e.enabled ?? true,
        steps: (e.steps ?? []).map((s) => ({
            id: newEscalationStepId(),
            delaySeconds: s.delay_seconds,
            recipientUserIds: s.recipient_users ?? [],
            recipientGroupIds: s.recipient_groups ?? [],
            subjectOverride: s.subject_override ?? "",
        })),
    };
}

/**
 * Build the wire payload for the nested `escalation` field.
 *
 * - Off + no steps → `null` (tells the backend to delete any existing policy).
 * - Otherwise → `{ enabled, steps: [...] }` with backend-ordered step indexes.
 *
 * Returning `null` rather than `undefined` is intentional: omit-on-PATCH means
 * "leave the existing policy alone," and we always want toggling escalation off
 * in the UI to actually delete the server-side policy.
 */
function escalationToWire(policy: EscalationPolicyDraft): {
    enabled: boolean;
    steps: {
        order: number;
        delay_seconds: number;
        recipient_users: number[];
        recipient_groups: string[];
        subject_override: string;
    }[];
} | null {
    const hasContent = policy.enabled || policy.steps.length > 0;
    if (!hasContent) return null;
    return {
        enabled: policy.enabled ?? false,
        steps: policy.steps.map((s, i) => ({
            order: i,
            delay_seconds: s.delaySeconds,
            recipient_users: s.recipientUserIds,
            recipient_groups: s.recipientGroupIds,
            subject_override: s.subjectOverride || "",
        })),
    };
}

export function blankRuleDraft(scope: RuleScope): RuleDraft {
    return {
        id: "",
        scope,
        name: "",
        description: "",
        eventCode: "ncr.opened",
        conditionsSource: "",
        channels: ["in_app"],
        priority: 0,
        enabled: true,
        minGapSeconds: 0,
        recipientStrategy: "static",
        recipientUserIds: [],
        recipientGroupIds: [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: null,
        escalation: emptyEscalation(),
    };
}

// =============================================================================
// Wire → Draft
// =============================================================================

function asChannelList(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((c): c is string => typeof c === "string")
        : [];
}

function asRecipientStrategy(value: unknown): RecipientStrategy {
    if (value === "from_payload" || value === "union") return value;
    return "static";
}

function commonRuleToDraft(rule: TenantRule | CustomerRule | PersonalRule) {
    return {
        id: rule.id,
        name: rule.name ?? "",
        description: rule.description ?? "",
        eventCode: rule.event_code ?? "",
        conditionsSource: rule.conditions_source ?? "",
        channels: asChannelList(rule.channels),
        priority: rule.priority ?? 0,
        enabled: rule.enabled ?? true,
        minGapSeconds: rule.min_gap_seconds ?? 0,
        recipientStrategy: asRecipientStrategy(
            (rule as { recipient_strategy?: unknown }).recipient_strategy,
        ),
    };
}

export function tenantRuleToDraft(rule: TenantRule): RuleDraft {
    return {
        ...commonRuleToDraft(rule),
        scope: "tenant",
        recipientUserIds: rule.recipient_users ?? [],
        recipientGroupIds: rule.recipient_groups ?? [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: null,
        escalation: escalationFromWire(rule.escalation),
    };
}

export function customerRuleToDraft(rule: CustomerRule): RuleDraft {
    return {
        ...commonRuleToDraft(rule),
        scope: "customer",
        recipientUserIds: rule.recipient_users ?? [],
        recipientGroupIds: rule.recipient_groups ?? [],
        scopeCustomerId: rule.scope_customer ?? "",
        recipientExternalIds: rule.recipient_external ?? [],
        ownerUserId: null,
        escalation: escalationFromWire(rule.escalation),
    };
}

export function personalRuleToDraft(rule: PersonalRule): RuleDraft {
    return {
        ...commonRuleToDraft(rule),
        scope: "personal",
        recipientUserIds: [],
        recipientGroupIds: [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: rule.owner_user ?? null,
        escalation: escalationFromWire(rule.escalation),
    };
}

// =============================================================================
// Draft → Wire
// =============================================================================
//
// Create and Patch shapes are structurally identical today, but we keep
// separate `*Create` and `*Patch` exports so each call site is explicit about
// intent. If the backend ever adds a create-only required field, the split
// already exists and the type check will catch the missing field.

function commonRulePayload(draft: RuleDraft) {
    return {
        name: draft.name,
        description: draft.description || undefined,
        event_code: draft.eventCode,
        conditions_source: draft.conditionsSource || undefined,
        channels: draft.channels,
        priority: draft.priority,
        enabled: draft.enabled,
        min_gap_seconds: draft.minGapSeconds,
        recipient_strategy: draft.recipientStrategy,
        escalation: escalationToWire(draft.escalation),
    };
}

function tenantPayload(draft: RuleDraft) {
    return {
        ...commonRulePayload(draft),
        recipient_users: draft.recipientUserIds,
        recipient_groups: draft.recipientGroupIds,
    };
}

function customerPayload(draft: RuleDraft) {
    return {
        ...commonRulePayload(draft),
        scope_customer: draft.scopeCustomerId,
        recipient_users: draft.recipientUserIds,
        recipient_groups: draft.recipientGroupIds,
        recipient_external: draft.recipientExternalIds,
    };
}

export const draftToTenantCreate = (draft: RuleDraft): TenantRuleRequest =>
    tenantPayload(draft);
export const draftToTenantPatch = (draft: RuleDraft): PatchedTenantRuleRequest =>
    tenantPayload(draft);

export const draftToCustomerCreate = (draft: RuleDraft): CustomerRuleRequest =>
    customerPayload(draft);
export const draftToCustomerPatch = (draft: RuleDraft): PatchedCustomerRuleRequest =>
    customerPayload(draft);

export const draftToPersonalCreate = (draft: RuleDraft): PersonalRuleRequest =>
    commonRulePayload(draft);
export const draftToPersonalPatch = (draft: RuleDraft): PatchedPersonalRuleRequest =>
    commonRulePayload(draft);