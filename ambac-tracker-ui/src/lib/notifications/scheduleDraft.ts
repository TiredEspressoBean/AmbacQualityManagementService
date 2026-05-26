/**
 * Editor-side draft type for NotificationSchedules and converters to/from
 * the three per-scope backend shapes.
 *
 * Mirrors `ruleDraft.ts`. The backend has three serializers (Tenant /
 * Customer / Personal) with mostly-overlapping fields plus scope-specific
 * extras; the editor mutates one unified draft and the converters resolve
 * the scope-specific wire shape on save.
 */
import type {
    CustomerSchedule,
    CustomerScheduleRequest,
    PatchedCustomerScheduleRequest,
    PatchedPersonalScheduleRequest,
    PatchedTenantScheduleRequest,
    PersonalSchedule,
    PersonalScheduleRequest,
    TenantSchedule,
    TenantScheduleRequest,
} from "@/hooks/notificationSchedules";

export type ScheduleScope = "tenant" | "customer" | "personal";

export const SCHEDULE_SCOPE_LABELS: Record<ScheduleScope, string> = {
    tenant: "Tenant-wide",
    customer: "Customer-scoped",
    personal: "Personal",
};

export type ScheduleCadence = "weekly" | "monthly";

export const CADENCE_LABELS: Record<ScheduleCadence, string> = {
    weekly: "Weekly",
    monthly: "Monthly",
};

export interface ScheduleDraft {
    id: string;
    scope: ScheduleScope;
    name: string;
    description: string;
    enabled: boolean;
    providerKind: string;
    providerParams: Record<string, unknown>;
    cadence: ScheduleCadence;
    dayOfWeek: number | null;   // 0=Mon..6=Sun
    dayOfMonth: number | null;  // 1-28
    timeOfDay: string;          // "HH:MM:SS" in `timezone`
    timezone: string;
    channels: string[];
    recipientUserIds: number[];
    recipientGroupIds: string[];
    scopeCustomerId: string;     // customer scope only
    recipientExternalIds: string[];  // customer scope only
    ownerUserId: number | null;  // personal scope, read-only
}

export function blankScheduleDraft(scope: ScheduleScope): ScheduleDraft {
    return {
        id: "",
        scope,
        name: "",
        description: "",
        enabled: true,
        providerKind: "customer_active_orders",
        providerParams: {},
        cadence: "weekly",
        dayOfWeek: 0,
        dayOfMonth: null,
        timeOfDay: "08:00:00",
        timezone: "UTC",
        channels: ["email"],
        recipientUserIds: [],
        recipientGroupIds: [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: null,
    };
}

// =============================================================================
// Wire → Draft
// =============================================================================

function asStringList(value: unknown): string[] {
    return Array.isArray(value)
        ? value.filter((c): c is string => typeof c === "string")
        : [];
}

function commonScheduleToDraft(row: TenantSchedule | CustomerSchedule | PersonalSchedule) {
    return {
        id: row.id,
        name: row.name ?? "",
        description: row.description ?? "",
        enabled: row.enabled ?? true,
        providerKind: row.provider_kind ?? "customer_active_orders",
        providerParams: (row.provider_params as Record<string, unknown>) ?? {},
        cadence: (row.cadence as ScheduleCadence) ?? "weekly",
        dayOfWeek: row.day_of_week ?? null,
        dayOfMonth: row.day_of_month ?? null,
        timeOfDay: row.time_of_day ?? "08:00:00",
        timezone: row.timezone ?? "UTC",
        channels: asStringList(row.channels),
    };
}

export function tenantScheduleToDraft(row: TenantSchedule): ScheduleDraft {
    return {
        ...commonScheduleToDraft(row),
        scope: "tenant",
        recipientUserIds: row.recipient_users ?? [],
        recipientGroupIds: row.recipient_groups ?? [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: null,
    };
}

export function customerScheduleToDraft(row: CustomerSchedule): ScheduleDraft {
    return {
        ...commonScheduleToDraft(row),
        scope: "customer",
        recipientUserIds: row.recipient_users ?? [],
        recipientGroupIds: row.recipient_groups ?? [],
        scopeCustomerId: row.scope_customer ?? "",
        recipientExternalIds: row.recipient_external ?? [],
        ownerUserId: null,
    };
}

export function personalScheduleToDraft(row: PersonalSchedule): ScheduleDraft {
    return {
        ...commonScheduleToDraft(row),
        scope: "personal",
        recipientUserIds: [],
        recipientGroupIds: [],
        scopeCustomerId: "",
        recipientExternalIds: [],
        ownerUserId: row.owner_user ?? null,
    };
}

// =============================================================================
// Draft → Wire
// =============================================================================

function commonPayload(draft: ScheduleDraft) {
    return {
        name: draft.name,
        description: draft.description || undefined,
        enabled: draft.enabled,
        provider_kind: draft.providerKind,
        provider_params: draft.providerParams,
        cadence: draft.cadence,
        day_of_week: draft.cadence === "weekly" ? draft.dayOfWeek : null,
        day_of_month: draft.cadence === "monthly" ? draft.dayOfMonth : null,
        time_of_day: draft.timeOfDay,
        timezone: draft.timezone,
        channels: draft.channels,
    };
}

function tenantPayload(draft: ScheduleDraft) {
    return {
        ...commonPayload(draft),
        recipient_users: draft.recipientUserIds,
        recipient_groups: draft.recipientGroupIds,
    };
}

function customerPayload(draft: ScheduleDraft) {
    return {
        ...commonPayload(draft),
        scope_customer: draft.scopeCustomerId,
        recipient_users: draft.recipientUserIds,
        recipient_groups: draft.recipientGroupIds,
        recipient_external: draft.recipientExternalIds,
    };
}

export const draftToTenantCreate = (draft: ScheduleDraft): TenantScheduleRequest =>
    tenantPayload(draft) as TenantScheduleRequest;
export const draftToTenantPatch = (draft: ScheduleDraft): PatchedTenantScheduleRequest =>
    tenantPayload(draft) as PatchedTenantScheduleRequest;

export const draftToCustomerCreate = (draft: ScheduleDraft): CustomerScheduleRequest =>
    customerPayload(draft) as CustomerScheduleRequest;
export const draftToCustomerPatch = (draft: ScheduleDraft): PatchedCustomerScheduleRequest =>
    customerPayload(draft) as PatchedCustomerScheduleRequest;

export const draftToPersonalCreate = (draft: ScheduleDraft): PersonalScheduleRequest =>
    commonPayload(draft) as PersonalScheduleRequest;
export const draftToPersonalPatch = (draft: ScheduleDraft): PatchedPersonalScheduleRequest =>
    commonPayload(draft) as PatchedPersonalScheduleRequest;
