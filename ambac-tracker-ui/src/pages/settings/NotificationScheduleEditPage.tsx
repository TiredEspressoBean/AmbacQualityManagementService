/**
 * Scheduled Reports — admin edit page.
 *
 * Routed at:
 *   /settings/notification-schedules/$scope/new
 *   /settings/notification-schedules/$scope/$scheduleId/edit
 *
 * `$scope` is 'tenant' | 'customer'. Personal schedules are managed from
 * `/profile/notifications`, not this page.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Save, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { BasicsCard } from "@/components/notifications/schedule-editor/BasicsCard";
import { ContentCard } from "@/components/notifications/schedule-editor/ContentCard";
import { DeliveryCard } from "@/components/notifications/schedule-editor/DeliveryCard";
import { RecipientsCard } from "@/components/notifications/schedule-editor/RecipientsCard";
import { ScheduleCard } from "@/components/notifications/schedule-editor/ScheduleCard";
import { ScopeCard } from "@/components/notifications/schedule-editor/ScopeCard";

import {
    useCreateCustomerSchedule,
    useCreateTenantSchedule,
    useDeleteCustomerSchedule,
    useDeleteTenantSchedule,
    useRetrieveCustomerSchedule,
    useRetrieveTenantSchedule,
    useUpdateCustomerSchedule,
    useUpdateTenantSchedule,
} from "@/hooks/notificationSchedules";

import {
    blankScheduleDraft,
    customerScheduleToDraft,
    draftToCustomerCreate,
    draftToCustomerPatch,
    draftToTenantCreate,
    draftToTenantPatch,
    SCHEDULE_SCOPE_LABELS,
    tenantScheduleToDraft,
    type ScheduleDraft,
    type ScheduleScope,
} from "@/lib/notifications/scheduleDraft";

type AdminScope = Exclude<ScheduleScope, "personal">;

export function NotificationScheduleEditPage({
    scheduleId,
    initialScope,
}: {
    scheduleId?: string;
    initialScope: AdminScope;
}) {
    const isNew = !scheduleId;

    const tenantQ = useRetrieveTenantSchedule(scheduleId ?? "", {
        enabled: !isNew && initialScope === "tenant",
    });
    const customerQ = useRetrieveCustomerSchedule(scheduleId ?? "", {
        enabled: !isNew && initialScope === "customer",
    });

    const activeQ = initialScope === "tenant" ? tenantQ : customerQ;

    const loadedDraft = useMemo<ScheduleDraft | null>(() => {
        if (isNew) return null;
        if (initialScope === "tenant" && tenantQ.data) return tenantScheduleToDraft(tenantQ.data);
        if (initialScope === "customer" && customerQ.data) return customerScheduleToDraft(customerQ.data);
        return null;
    }, [isNew, initialScope, tenantQ.data, customerQ.data]);

    if (!isNew && !loadedDraft && !activeQ.isPending) {
        return (
            <div className="container mx-auto p-6 max-w-7xl">
                <p className="text-sm text-muted-foreground">Schedule not found.</p>
            </div>
        );
    }

    if (isNew || loadedDraft) {
        return (
            <EditorBody
                key={loadedDraft?.id ?? "new"}
                initialDraft={loadedDraft ?? blankScheduleDraft(initialScope)}
                isNew={isNew}
            />
        );
    }

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <p className="text-sm text-muted-foreground">Loading schedule…</p>
        </div>
    );
}

function EditorBody({
    initialDraft,
    isNew,
}: {
    initialDraft: ScheduleDraft;
    isNew: boolean;
}) {
    const navigate = useNavigate();
    const [draft, setDraft] = useState<ScheduleDraft>(initialDraft);
    const patch = (updates: Partial<ScheduleDraft>) =>
        setDraft((current) => ({ ...current, ...updates }));

    const close = () => navigate({ to: "/settings/notification-rules" });

    const createTenant = useCreateTenantSchedule();
    const createCustomer = useCreateCustomerSchedule();
    const updateTenant = useUpdateTenantSchedule();
    const updateCustomer = useUpdateCustomerSchedule();
    const deleteTenant = useDeleteTenantSchedule();
    const deleteCustomer = useDeleteCustomerSchedule();

    const saving =
        createTenant.isPending ||
        createCustomer.isPending ||
        updateTenant.isPending ||
        updateCustomer.isPending;

    const save = () => {
        const onSuccess = () => close();
        if (isNew) {
            if (draft.scope === "tenant")
                createTenant.mutate(draftToTenantCreate(draft), { onSuccess });
            else if (draft.scope === "customer")
                createCustomer.mutate(draftToCustomerCreate(draft), { onSuccess });
        } else {
            if (draft.scope === "tenant")
                updateTenant.mutate(
                    { id: draft.id, data: draftToTenantPatch(draft) },
                    { onSuccess },
                );
            else if (draft.scope === "customer")
                updateCustomer.mutate(
                    { id: draft.id, data: draftToCustomerPatch(draft) },
                    { onSuccess },
                );
        }
    };

    const remove = () => {
        if (!draft.id) return;
        const onSuccess = () => close();
        if (draft.scope === "tenant") deleteTenant.mutate(draft.id, { onSuccess });
        else if (draft.scope === "customer") deleteCustomer.mutate(draft.id, { onSuccess });
    };

    const canSave =
        draft.name.trim().length > 0 &&
        !saving &&
        (draft.scope !== "customer" || Boolean(draft.scopeCustomerId)) &&
        draft.channels.length > 0;

    return (
        <div className="container mx-auto p-6 max-w-7xl">
            <div className="sticky top-0 z-10 -mx-6 px-6 pt-6 pb-4 mb-6 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b">
                <div className="flex items-center justify-between gap-4 mb-3">
                    <Link
                        to="/settings/notification-rules"
                        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        All schedules
                    </Link>
                    <div className="flex items-center gap-2 shrink-0">
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
                            {isNew ? "Create schedule" : "Save changes"}
                        </Button>
                    </div>
                </div>
                <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                        {isNew ? "New schedule" : "Edit schedule"}
                    </span>
                    <Badge variant="secondary">{SCHEDULE_SCOPE_LABELS[draft.scope]}</Badge>
                </div>
                <p className="text-xl font-semibold leading-tight">
                    {draft.name || "Untitled schedule"}
                </p>
            </div>

            <div className="space-y-6 max-w-4xl">
                <BasicsCard draft={draft} patch={patch} />
                <ScopeCard draft={draft} patch={patch} lockedScope={!isNew} hidePersonal />
                <ContentCard draft={draft} patch={patch} />
                <ScheduleCard draft={draft} patch={patch} />
                <RecipientsCard draft={draft} patch={patch} />
                <DeliveryCard draft={draft} patch={patch} />
            </div>
        </div>
    );
}

export default NotificationScheduleEditPage;
