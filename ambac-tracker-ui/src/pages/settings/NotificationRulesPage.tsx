/**
 * Notifications admin page — combined rule + schedule management.
 *
 * Top-level tabs: Rules | Schedules.
 * Each section has its own scope sub-tabs (Tenant / Customer / Personal for
 * rules; Tenant / Customer for schedules — personal schedules are managed
 * from /profile/notifications, not here).
 *
 * Routed at /settings/notification-rules (URL stays the same for now to
 * avoid breaking bookmarks). Rule edit pages route off
 * `/settings/notification-rules/$scope/$ruleId/edit`; schedule edit pages
 * route off `/settings/notification-schedules/$scope/$scheduleId/edit`.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Bell, Building2, CalendarClock, Pencil, Plus, Trash2, User as UserIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import { useTenantGroups } from "@/hooks/useTenantGroups";
import {
    useCustomerRules,
    useDeleteCustomerRule,
    useDeletePersonalRule,
    useDeleteTenantRule,
    usePersonalRules,
    useTenantRules,
    useUpdateCustomerRule,
    useUpdatePersonalRule,
    useUpdateTenantRule,
    type CustomerRule,
    type PersonalRule,
    type TenantRule,
} from "@/hooks/notificationRules";
import {
    useCustomerSchedules,
    useDeleteCustomerSchedule,
    useDeleteTenantSchedule,
    useScheduledContentProviders,
    useTenantSchedules,
    useUpdateCustomerSchedule,
    useUpdateTenantSchedule,
    type CustomerSchedule,
    type TenantSchedule,
} from "@/hooks/notificationSchedules";
import { useNotificationEventCatalog } from "@/lib/notifications/eventCatalog";

type Scope = "tenant" | "customer" | "personal";

const SCOPE_LABELS: Record<Scope, string> = {
    tenant: "Tenant-wide",
    customer: "Customer-scoped",
    personal: "Personal",
};

const SCOPE_DESCRIPTIONS: Record<Scope, string> = {
    tenant: "Fire for any matching event tenant-wide. Admin-authored.",
    customer:
        "Fire only when the event references a specific customer. Used for outbound notifications to ExternalContacts at that customer.",
    personal:
        "Each user authors their own rules. Owner is the implicit recipient — no recipient picker needed.",
};

type Section = "rules" | "schedules";
type AdminScope = "tenant" | "customer";

export function NotificationRulesPage() {
    const navigate = useNavigate();
    const [section, setSection] = useState<Section>("rules");
    const [ruleScopeTab, setRuleScopeTab] = useState<Scope>("tenant");
    const [scheduleScopeTab, setScheduleScopeTab] = useState<AdminScope>("tenant");

    const handleNewRule = () =>
        navigate({
            to: "/settings/notification-rules/$scope/new",
            params: { scope: ruleScopeTab },
        });

    const handleEditRule = (id: string, scope: Scope) =>
        navigate({
            to: "/settings/notification-rules/$scope/$ruleId/edit",
            params: { scope, ruleId: id },
        });

    const handleNewSchedule = () =>
        navigate({
            to: "/settings/notification-schedules/$scope/new",
            params: { scope: scheduleScopeTab },
        });

    const handleEditSchedule = (id: string, scope: AdminScope) =>
        navigate({
            to: "/settings/notification-schedules/$scope/$scheduleId/edit",
            params: { scope, scheduleId: id },
        });

    const newButton =
        section === "rules" ? (
            <Button onClick={handleNewRule} className="shrink-0">
                <Plus className="h-4 w-4 mr-2" />
                New rule
            </Button>
        ) : (
            <Button onClick={handleNewSchedule} className="shrink-0">
                <Plus className="h-4 w-4 mr-2" />
                New schedule
            </Button>
        );

    return (
        <div className="container mx-auto p-6 max-w-6xl">
            <div className="mb-6">
                <Link
                    to="/settings"
                    className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
                >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Settings
                </Link>
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <Bell className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold">Notifications</h1>
                            <p className="text-muted-foreground text-sm">
                                Event-driven rules and recurring scheduled digests.
                            </p>
                        </div>
                    </div>
                    {newButton}
                </div>
            </div>

            <Tabs value={section} onValueChange={(v) => setSection(v as Section)}>
                <TabsList>
                    <TabsTrigger value="rules">
                        <Bell className="h-4 w-4 mr-2" />
                        Rules
                    </TabsTrigger>
                    <TabsTrigger value="schedules">
                        <CalendarClock className="h-4 w-4 mr-2" />
                        Schedules
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="rules" className="mt-4">
                    <Tabs value={ruleScopeTab} onValueChange={(v) => setRuleScopeTab(v as Scope)}>
                        <TabsList>
                            <TabsTrigger value="tenant">
                                <Building2 className="h-4 w-4 mr-2" />
                                Tenant-wide
                            </TabsTrigger>
                            <TabsTrigger value="customer">
                                <Building2 className="h-4 w-4 mr-2" />
                                Customer-scoped
                            </TabsTrigger>
                            <TabsTrigger value="personal">
                                <UserIcon className="h-4 w-4 mr-2" />
                                Personal
                            </TabsTrigger>
                        </TabsList>
                        <TabsContent value="tenant" className="mt-4">
                            <TenantRulesCard onEdit={(id) => handleEditRule(id, "tenant")} />
                        </TabsContent>
                        <TabsContent value="customer" className="mt-4">
                            <CustomerRulesCard onEdit={(id) => handleEditRule(id, "customer")} />
                        </TabsContent>
                        <TabsContent value="personal" className="mt-4">
                            <PersonalRulesCard onEdit={(id) => handleEditRule(id, "personal")} />
                        </TabsContent>
                    </Tabs>
                </TabsContent>

                <TabsContent value="schedules" className="mt-4">
                    <Tabs
                        value={scheduleScopeTab}
                        onValueChange={(v) => setScheduleScopeTab(v as AdminScope)}
                    >
                        <TabsList>
                            <TabsTrigger value="tenant">
                                <Building2 className="h-4 w-4 mr-2" />
                                Tenant-wide
                            </TabsTrigger>
                            <TabsTrigger value="customer">
                                <Building2 className="h-4 w-4 mr-2" />
                                Customer-scoped
                            </TabsTrigger>
                        </TabsList>
                        <TabsContent value="tenant" className="mt-4">
                            <TenantSchedulesCard
                                onEdit={(id) => handleEditSchedule(id, "tenant")}
                            />
                        </TabsContent>
                        <TabsContent value="customer" className="mt-4">
                            <CustomerSchedulesCard
                                onEdit={(id) => handleEditSchedule(id, "customer")}
                            />
                        </TabsContent>
                    </Tabs>
                </TabsContent>
            </Tabs>
        </div>
    );
}

// =============================================================================
// Scope cards — one query each, only fires when its tab is mounted.
// =============================================================================

function TenantRulesCard({ onEdit }: { onEdit: (id: string) => void }) {
    const { data, isLoading } = useTenantRules();
    const { data: groupsResp } = useTenantGroups();
    const updateRule = useUpdateTenantRule();
    const deleteRule = useDeleteTenantRule();

    const groupNameById = useMemo(() => {
        const map = new Map<string, string>();
        for (const g of groupsResp?.results ?? []) map.set(String(g.id), g.name);
        return map;
    }, [groupsResp]);

    return (
        <ScopeCard scope="tenant">
            {renderTable({
                isLoading,
                rules: data?.results ?? [],
                renderRow: (r: TenantRule) => (
                    <TenantRuleRow
                        key={r.id}
                        rule={r}
                        groupNameById={groupNameById}
                        onEdit={() => onEdit(r.id)}
                        onToggle={(enabled) =>
                            updateRule.mutate({ id: r.id, data: { enabled } })
                        }
                        onDelete={() => deleteRule.mutate(r.id)}
                    />
                ),
            })}
        </ScopeCard>
    );
}

function CustomerRulesCard({ onEdit }: { onEdit: (id: string) => void }) {
    const { data, isLoading } = useCustomerRules();
    const { data: groupsResp } = useTenantGroups();
    const { data: companiesResp } = useRetrieveCompanies();
    const updateRule = useUpdateCustomerRule();
    const deleteRule = useDeleteCustomerRule();

    const groupNameById = useMemo(() => {
        const map = new Map<string, string>();
        for (const g of groupsResp?.results ?? []) map.set(String(g.id), g.name);
        return map;
    }, [groupsResp]);

    const companyNameById = useMemo(() => {
        const map = new Map<string, string>();
        for (const c of companiesResp?.results ?? []) map.set(String(c.id), c.name);
        return map;
    }, [companiesResp]);

    return (
        <ScopeCard scope="customer">
            {renderTable({
                isLoading,
                rules: data?.results ?? [],
                renderRow: (r: CustomerRule) => (
                    <CustomerRuleRow
                        key={r.id}
                        rule={r}
                        groupNameById={groupNameById}
                        companyNameById={companyNameById}
                        onEdit={() => onEdit(r.id)}
                        onToggle={(enabled) =>
                            updateRule.mutate({ id: r.id, data: { enabled } })
                        }
                        onDelete={() => deleteRule.mutate(r.id)}
                    />
                ),
            })}
        </ScopeCard>
    );
}

function PersonalRulesCard({ onEdit }: { onEdit: (id: string) => void }) {
    const { data, isLoading } = usePersonalRules();
    const updateRule = useUpdatePersonalRule();
    const deleteRule = useDeletePersonalRule();

    return (
        <ScopeCard scope="personal">
            {renderTable({
                isLoading,
                rules: data?.results ?? [],
                renderRow: (r: PersonalRule) => (
                    <PersonalRuleRow
                        key={r.id}
                        rule={r}
                        onEdit={() => onEdit(r.id)}
                        onToggle={(enabled) =>
                            updateRule.mutate({ id: r.id, data: { enabled } })
                        }
                        onDelete={() => deleteRule.mutate(r.id)}
                    />
                ),
            })}
        </ScopeCard>
    );
}

// =============================================================================
// Shared UI bits
// =============================================================================

function ScopeCard({ scope, children }: { scope: Scope; children: React.ReactNode }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">{SCOPE_LABELS[scope]}</CardTitle>
                <CardDescription>{SCOPE_DESCRIPTIONS[scope]}</CardDescription>
            </CardHeader>
            <CardContent>{children}</CardContent>
        </Card>
    );
}

function renderTable<T extends { id: string }>({
    isLoading,
    rules,
    renderRow,
}: {
    isLoading: boolean;
    rules: T[];
    renderRow: (rule: T) => React.ReactNode;
}) {
    if (isLoading) {
        return <p className="text-sm text-muted-foreground py-8 text-center">Loading…</p>;
    }
    if (rules.length === 0) {
        return (
            <p className="text-sm text-muted-foreground py-8 text-center">
                No rules in this scope yet.
            </p>
        );
    }
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Event</TableHead>
                    <TableHead>When</TableHead>
                    <TableHead>Recipients</TableHead>
                    <TableHead>Channels</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead />
                </TableRow>
            </TableHeader>
            <TableBody>{rules.map(renderRow)}</TableBody>
        </Table>
    );
}

function EventCell({ eventCode }: { eventCode: string | undefined }) {
    const { events } = useNotificationEventCatalog();
    const event = events.find((e) => e.code === eventCode);
    return <Badge variant="outline">{event?.label ?? eventCode ?? "—"}</Badge>;
}

function ConditionsCell({ source }: { source: string | undefined }) {
    if (!source) return <span className="text-xs text-muted-foreground">always</span>;
    return (
        <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono break-all">
            {source}
        </code>
    );
}

function ChannelsCell({ channels }: { channels: readonly string[] }) {
    return (
        <div className="flex gap-1">
            {channels.includes("in_app") && <Badge variant="secondary">In-app</Badge>}
            {channels.includes("email") && <Badge variant="secondary">Email</Badge>}
        </div>
    );
}

function RowActions({
    enabled,
    onToggle,
    onEdit,
    onDelete,
}: {
    enabled: boolean;
    onToggle: (enabled: boolean) => void;
    onEdit: () => void;
    onDelete: () => void;
}) {
    return (
        <>
            <TableCell>
                <Switch checked={enabled} onCheckedChange={onToggle} />
            </TableCell>
            <TableCell className="text-right">
                <Button size="icon" variant="ghost" aria-label="Edit" onClick={onEdit}>
                    <Pencil className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" aria-label="Delete" onClick={onDelete}>
                    <Trash2 className="h-4 w-4" />
                </Button>
            </TableCell>
        </>
    );
}

// Backend `channels` is typed as `unknown` in the zod-derived schemas
// (JSONField). Narrow it for display.
function asChannelList(channels: unknown): string[] {
    return Array.isArray(channels) ? channels.filter((c): c is string => typeof c === "string") : [];
}

// =============================================================================
// Per-scope rows
// =============================================================================

function TenantRuleRow({
    rule,
    groupNameById,
    onEdit,
    onToggle,
    onDelete,
}: {
    rule: TenantRule;
    groupNameById: Map<string, string>;
    onEdit: () => void;
    onToggle: (enabled: boolean) => void;
    onDelete: () => void;
}) {
    return (
        <TableRow>
            <TableCell className="font-medium">
                <button className="text-left hover:underline" onClick={onEdit}>
                    {rule.name || <em className="text-muted-foreground">(unnamed)</em>}
                </button>
            </TableCell>
            <TableCell><EventCell eventCode={rule.event_code} /></TableCell>
            <TableCell className="max-w-[280px]"><ConditionsCell source={rule.conditions_source} /></TableCell>
            <TableCell className="max-w-[200px]">
                <RecipientSummary
                    userCount={rule.recipient_users?.length ?? 0}
                    groupIds={rule.recipient_groups ?? []}
                    groupNameById={groupNameById}
                    externalCount={0}
                />
            </TableCell>
            <TableCell><ChannelsCell channels={asChannelList(rule.channels)} /></TableCell>
            <RowActions
                enabled={rule.enabled ?? true}
                onToggle={onToggle}
                onEdit={onEdit}
                onDelete={onDelete}
            />
        </TableRow>
    );
}

function CustomerRuleRow({
    rule,
    groupNameById,
    companyNameById,
    onEdit,
    onToggle,
    onDelete,
}: {
    rule: CustomerRule;
    groupNameById: Map<string, string>;
    companyNameById: Map<string, string>;
    onEdit: () => void;
    onToggle: (enabled: boolean) => void;
    onDelete: () => void;
}) {
    const customerName = rule.scope_customer
        ? companyNameById.get(String(rule.scope_customer))
        : undefined;
    return (
        <TableRow>
            <TableCell className="font-medium">
                <button className="text-left hover:underline" onClick={onEdit}>
                    {rule.name || <em className="text-muted-foreground">(unnamed)</em>}
                </button>
                {customerName && (
                    <div className="text-xs text-muted-foreground mt-0.5">{customerName}</div>
                )}
            </TableCell>
            <TableCell><EventCell eventCode={rule.event_code} /></TableCell>
            <TableCell className="max-w-[280px]"><ConditionsCell source={rule.conditions_source} /></TableCell>
            <TableCell className="max-w-[200px]">
                <RecipientSummary
                    userCount={rule.recipient_users?.length ?? 0}
                    groupIds={rule.recipient_groups ?? []}
                    groupNameById={groupNameById}
                    externalCount={rule.recipient_external?.length ?? 0}
                />
            </TableCell>
            <TableCell><ChannelsCell channels={asChannelList(rule.channels)} /></TableCell>
            <RowActions
                enabled={rule.enabled ?? true}
                onToggle={onToggle}
                onEdit={onEdit}
                onDelete={onDelete}
            />
        </TableRow>
    );
}

function PersonalRuleRow({
    rule,
    onEdit,
    onToggle,
    onDelete,
}: {
    rule: PersonalRule;
    onEdit: () => void;
    onToggle: (enabled: boolean) => void;
    onDelete: () => void;
}) {
    return (
        <TableRow>
            <TableCell className="font-medium">
                <button className="text-left hover:underline" onClick={onEdit}>
                    {rule.name || <em className="text-muted-foreground">(unnamed)</em>}
                </button>
            </TableCell>
            <TableCell><EventCell eventCode={rule.event_code} /></TableCell>
            <TableCell className="max-w-[280px]"><ConditionsCell source={rule.conditions_source} /></TableCell>
            <TableCell className="max-w-[200px]">
                <span className="text-xs text-muted-foreground">rule owner</span>
            </TableCell>
            <TableCell><ChannelsCell channels={asChannelList(rule.channels)} /></TableCell>
            <RowActions
                enabled={rule.enabled ?? true}
                onToggle={onToggle}
                onEdit={onEdit}
                onDelete={onDelete}
            />
        </TableRow>
    );
}

function RecipientSummary({
    userCount,
    groupIds,
    groupNameById,
    externalCount,
}: {
    userCount: number;
    groupIds: readonly string[];
    groupNameById: Map<string, string>;
    externalCount: number;
}) {
    const parts: string[] = [];
    if (groupIds.length) {
        const names = groupIds
            .map((id) => groupNameById.get(String(id)))
            .filter((n): n is string => Boolean(n));
        if (names.length) parts.push(names.join(", "));
        else parts.push(`${groupIds.length} group(s)`);
    }
    if (userCount) parts.push(`${userCount} user(s)`);
    if (externalCount) parts.push(`${externalCount} external`);
    if (!parts.length) return <span className="text-xs text-muted-foreground">none</span>;
    return <span className="text-xs">{parts.join(" · ")}</span>;
}

// =============================================================================
// Schedules section — admin scopes only (personal lives under /profile/notifications).
// =============================================================================

const DAYS_OF_WEEK_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function scheduleCadenceSummary(row: TenantSchedule | CustomerSchedule): string {
    const time = (row.time_of_day ?? "").slice(0, 5);
    if (row.cadence === "weekly" && row.day_of_week !== null && row.day_of_week !== undefined) {
        return `Weekly · ${DAYS_OF_WEEK_SHORT[row.day_of_week]} ${time} ${row.timezone ?? "UTC"}`;
    }
    if (row.cadence === "monthly" && row.day_of_month) {
        return `Monthly · day ${row.day_of_month} ${time} ${row.timezone ?? "UTC"}`;
    }
    return row.cadence ?? "—";
}

function TenantSchedulesCard({ onEdit }: { onEdit: (id: string) => void }) {
    const { data, isLoading } = useTenantSchedules();
    const { data: providers } = useScheduledContentProviders();
    const update = useUpdateTenantSchedule();
    const del = useDeleteTenantSchedule();

    const providerLabelByName = useMemo(() => {
        const m = new Map<string, string>();
        for (const p of providers ?? []) m.set(p.name, p.title);
        return m;
    }, [providers]);

    return (
        <ScheduleScopeCard
            title="Tenant-wide schedules"
            description="Recurring deliveries fired across the whole tenant. Recipients are internal users/groups."
        >
            {renderScheduleTable({
                isLoading,
                rows: data?.results ?? [],
                renderRow: (r: TenantSchedule) => (
                    <ScheduleRow
                        key={r.id}
                        row={r}
                        providerLabel={providerLabelByName.get(r.provider_kind) ?? r.provider_kind}
                        onEdit={() => onEdit(r.id)}
                        onToggle={(enabled) =>
                            update.mutate({ id: r.id, data: { enabled } })
                        }
                        onDelete={() => del.mutate(r.id)}
                    />
                ),
            })}
        </ScheduleScopeCard>
    );
}

function CustomerSchedulesCard({ onEdit }: { onEdit: (id: string) => void }) {
    const { data, isLoading } = useCustomerSchedules();
    const { data: providers } = useScheduledContentProviders();
    const { data: companiesResp } = useRetrieveCompanies();
    const update = useUpdateCustomerSchedule();
    const del = useDeleteCustomerSchedule();

    const providerLabelByName = useMemo(() => {
        const m = new Map<string, string>();
        for (const p of providers ?? []) m.set(p.name, p.title);
        return m;
    }, [providers]);

    const companyNameById = useMemo(() => {
        const m = new Map<string, string>();
        for (const c of companiesResp?.results ?? []) m.set(String(c.id), c.name);
        return m;
    }, [companiesResp]);

    return (
        <ScheduleScopeCard
            title="Customer-scoped schedules"
            description="Recurring deliveries for one customer organization. Used for outbound digests to ExternalContacts."
        >
            {renderScheduleTable({
                isLoading,
                rows: data?.results ?? [],
                renderRow: (r: CustomerSchedule) => (
                    <ScheduleRow
                        key={r.id}
                        row={r}
                        providerLabel={providerLabelByName.get(r.provider_kind) ?? r.provider_kind}
                        customerName={
                            r.scope_customer
                                ? companyNameById.get(String(r.scope_customer))
                                : undefined
                        }
                        onEdit={() => onEdit(r.id)}
                        onToggle={(enabled) =>
                            update.mutate({ id: r.id, data: { enabled } })
                        }
                        onDelete={() => del.mutate(r.id)}
                    />
                ),
            })}
        </ScheduleScopeCard>
    );
}

function ScheduleScopeCard({
    title,
    description,
    children,
}: {
    title: string;
    description: string;
    children: React.ReactNode;
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>{children}</CardContent>
        </Card>
    );
}

function renderScheduleTable<T extends { id: string }>({
    isLoading,
    rows,
    renderRow,
}: {
    isLoading: boolean;
    rows: T[];
    renderRow: (row: T) => React.ReactNode;
}) {
    if (isLoading) {
        return <p className="text-sm text-muted-foreground py-8 text-center">Loading…</p>;
    }
    if (rows.length === 0) {
        return (
            <p className="text-sm text-muted-foreground py-8 text-center">
                No schedules in this scope yet.
            </p>
        );
    }
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Report</TableHead>
                    <TableHead>Cadence</TableHead>
                    <TableHead>Channels</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead />
                </TableRow>
            </TableHeader>
            <TableBody>{rows.map(renderRow)}</TableBody>
        </Table>
    );
}

function ScheduleRow({
    row,
    providerLabel,
    customerName,
    onEdit,
    onToggle,
    onDelete,
}: {
    row: TenantSchedule | CustomerSchedule;
    providerLabel: string;
    customerName?: string;
    onEdit: () => void;
    onToggle: (enabled: boolean) => void;
    onDelete: () => void;
}) {
    const channels = asChannelList(row.channels);
    return (
        <TableRow>
            <TableCell className="font-medium">
                <button className="text-left hover:underline" onClick={onEdit}>
                    {row.name || <em className="text-muted-foreground">(unnamed)</em>}
                </button>
                {customerName && (
                    <div className="text-xs text-muted-foreground mt-0.5">{customerName}</div>
                )}
            </TableCell>
            <TableCell><Badge variant="outline">{providerLabel}</Badge></TableCell>
            <TableCell className="text-xs">{scheduleCadenceSummary(row)}</TableCell>
            <TableCell>
                <div className="flex gap-1">
                    {channels.includes("email") && <Badge variant="secondary">Email</Badge>}
                </div>
            </TableCell>
            <TableCell>
                <Switch checked={row.enabled ?? true} onCheckedChange={onToggle} />
            </TableCell>
            <TableCell className="text-right">
                <Button size="icon" variant="ghost" aria-label="Edit" onClick={onEdit}>
                    <Pencil className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" aria-label="Delete" onClick={onDelete}>
                    <Trash2 className="h-4 w-4" />
                </Button>
            </TableCell>
        </TableRow>
    );
}

export default NotificationRulesPage;