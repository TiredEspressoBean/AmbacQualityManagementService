import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, Bell, Pencil, Plus, Trash2 } from "lucide-react";

import { api, type NotificationRule } from "@/lib/api/generated";
import { useContentTypeMapping } from "@/hooks/useContentTypes";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    RadioGroup,
    RadioGroupItem,
} from "@/components/ui/radio-group";

// ---------------------------------------------------------------------------
// Types derived from the generated client
// ---------------------------------------------------------------------------

type EventCatalogEntry = {
    key: string;
    label: string;
    description: string;
    scope_model: string | null;
    scope_label: string | null;
    resolver_keys: string[];
};

const NONE = "__none__";

const formSchema = z.object({
    name: z.string().min(1, "Name is required").max(200),
    description: z.string().optional(),
    event_type: z.string().min(1, "Event type is required"),
    channel_type: z.enum(["EMAIL", "IN_APP"]),
    scope_mode: z.enum(["any", "specific"]),
    scope_object_id: z.string().optional(),
    recipient_user_ids: z.array(z.number()),
    recipient_group_ids: z.array(z.string()),
    recipient_resolver_key: z.string(),
    cooldown_minutes: z.coerce.number().int().min(0),
    is_active: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

const defaultFormValues: FormValues = {
    name: "",
    description: "",
    event_type: "STEP_FAILURE",
    channel_type: "EMAIL",
    scope_mode: "any",
    scope_object_id: "",
    recipient_user_ids: [],
    recipient_group_ids: [],
    recipient_resolver_key: NONE,
    cooldown_minutes: 60,
    is_active: true,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useNotificationRules() {
    return useQuery({
        queryKey: ["notificationRules"],
        queryFn: () => api.api_NotificationRules_list({}),
    });
}

function useEventCatalog() {
    return useQuery<EventCatalogEntry[]>({
        queryKey: ["notificationEventTypes"],
        queryFn: () => api.api_NotificationEventTypes_list(),
    });
}

function useEmployeeOptions() {
    return useQuery({
        queryKey: ["employeeOptions"],
        queryFn: () => api.api_Employees_Options_list({}),
    });
}

function useTenantGroupOptions() {
    return useQuery({
        queryKey: ["tenantGroupOptions"],
        queryFn: () => api.api_TenantGroups_list({}),
    });
}

function useStepOptions() {
    return useQuery({
        queryKey: ["stepOptions"],
        queryFn: () => api.api_Steps_list({ queries: { limit: 500 } }),
    });
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function NotificationRulesPage() {
    const queryClient = useQueryClient();
    const { data: rulesResp, isLoading } = useNotificationRules();
    const { data: catalog } = useEventCatalog();

    const [editing, setEditing] = useState<NotificationRule | null>(null);
    const [isDialogOpen, setDialogOpen] = useState(false);
    const [pendingDelete, setPendingDelete] = useState<NotificationRule | null>(
        null
    );

    const rules = (rulesResp?.results ?? []) as NotificationRule[];

    const deleteMutation = useMutation({
        mutationFn: (id: string) =>
            api.api_NotificationRules_destroy(undefined, { params: { id } }),
        onSuccess: () => {
            toast.success("Rule deleted");
            queryClient.invalidateQueries({ queryKey: ["notificationRules"] });
            setPendingDelete(null);
        },
        onError: (e: Error) => toast.error(e.message || "Delete failed"),
    });

    const handleNew = () => {
        setEditing(null);
        setDialogOpen(true);
    };
    const handleEdit = (rule: NotificationRule) => {
        setEditing(rule);
        setDialogOpen(true);
    };

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            {/* Header */}
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
                            <h1 className="text-2xl font-bold">Notification Rules</h1>
                            <p className="text-muted-foreground text-sm">
                                Configure who gets notified when events happen in your tenant.
                            </p>
                        </div>
                    </div>
                    <Button onClick={handleNew} className="shrink-0">
                        <Plus className="h-4 w-4 mr-2" />
                        New Rule
                    </Button>
                </div>
            </div>

            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg">Active rules</CardTitle>
                    <CardDescription>
                        {rules.length === 0
                            ? "No rules yet. Click \"New Rule\" to create the first one."
                            : `${rules.length} rule${rules.length === 1 ? "" : "s"}`}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : rules.length === 0 ? null : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead>Event</TableHead>
                                    <TableHead>Channel</TableHead>
                                    <TableHead>Cooldown</TableHead>
                                    <TableHead>Active</TableHead>
                                    <TableHead className="w-24"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {rules.map((rule) => (
                                    <TableRow key={rule.id}>
                                        <TableCell className="font-medium">
                                            <button
                                                className="text-left hover:underline"
                                                onClick={() => handleEdit(rule)}
                                            >
                                                {rule.name}
                                            </button>
                                            {rule.description && (
                                                <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                                                    {rule.description}
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline">
                                                {catalog?.find((c) => c.key === rule.event_type)
                                                    ?.label ?? rule.event_type}
                                            </Badge>
                                            {rule.scope_object_id ? (
                                                <div className="text-xs text-muted-foreground mt-0.5">
                                                    scoped
                                                </div>
                                            ) : (
                                                <div className="text-xs text-muted-foreground mt-0.5">
                                                    all occurrences
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell>{rule.channel_type ?? "EMAIL"}</TableCell>
                                        <TableCell>
                                            {formatCooldown(rule.min_gap_seconds ?? 3600)}
                                        </TableCell>
                                        <TableCell>
                                            {rule.is_active ? (
                                                <Badge>Active</Badge>
                                            ) : (
                                                <Badge variant="secondary">Paused</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                size="icon"
                                                variant="ghost"
                                                onClick={() => handleEdit(rule)}
                                                aria-label="Edit"
                                            >
                                                <Pencil className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                size="icon"
                                                variant="ghost"
                                                onClick={() => setPendingDelete(rule)}
                                                aria-label="Delete"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <RuleDialog
                key={editing?.id ?? "new"}
                open={isDialogOpen}
                onOpenChange={setDialogOpen}
                rule={editing}
                catalog={catalog ?? []}
            />

            <AlertDialog
                open={pendingDelete !== null}
                onOpenChange={(open) => !open && setPendingDelete(null)}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete this rule?</AlertDialogTitle>
                        <AlertDialogDescription>
                            &quot;{pendingDelete?.name}&quot; will stop sending notifications
                            immediately. Already-queued notifications will still send.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() =>
                                pendingDelete && deleteMutation.mutate(pendingDelete.id)
                            }
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Dialog
// ---------------------------------------------------------------------------

function RuleDialog({
    open,
    onOpenChange,
    rule,
    catalog,
}: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    rule: NotificationRule | null;
    catalog: EventCatalogEntry[];
}) {
    const queryClient = useQueryClient();
    const { getContentTypeId } = useContentTypeMapping();
    const { data: employees } = useEmployeeOptions();
    const { data: groupsResp } = useTenantGroupOptions();
    const { data: stepsResp } = useStepOptions();

    const employeeList = employees ?? [];
    const groupList = (groupsResp?.results ?? []) as Array<{ id: string; name: string }>;
    const stepList = (stepsResp?.results ?? []) as Array<{ id: string; name: string }>;

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: rule
            ? ruleToForm(rule)
            : defaultFormValues,
    });

    const selectedEventKey = form.watch("event_type");
    const scopeMode = form.watch("scope_mode");
    const selectedEvent = useMemo(
        () => catalog.find((c) => c.key === selectedEventKey),
        [catalog, selectedEventKey]
    );

    const saveMutation = useMutation({
        mutationFn: async (values: FormValues) => {
            // Resolve the ContentType ID for the selected event's scope_model
            const scopeContentTypeId =
                values.scope_mode === "specific" && selectedEvent?.scope_model
                    ? getContentTypeId(
                          selectedEvent.scope_model.split(".")[1].toLowerCase()
                      )
                    : null;

            const body = {
                name: values.name,
                description: values.description || "",
                event_type: values.event_type as "STEP_FAILURE",
                channel_type: values.channel_type,
                scope_content_type:
                    values.scope_mode === "specific" ? scopeContentTypeId ?? null : null,
                scope_object_id:
                    values.scope_mode === "specific" ? values.scope_object_id || null : null,
                recipient_users: values.recipient_user_ids,
                recipient_groups: values.recipient_group_ids,
                recipient_resolver_key:
                    values.recipient_resolver_key === NONE
                        ? ""
                        : values.recipient_resolver_key,
                min_gap_seconds: values.cooldown_minutes * 60,
                is_active: values.is_active,
            };

            if (rule) {
                return api.api_NotificationRules_update(body, {
                    params: { id: rule.id },
                });
            }
            return api.api_NotificationRules_create(body);
        },
        onSuccess: () => {
            toast.success(rule ? "Rule updated" : "Rule created");
            queryClient.invalidateQueries({ queryKey: ["notificationRules"] });
            onOpenChange(false);
        },
        onError: (e: Error) => toast.error(e.message || "Save failed"),
    });

    const hasRecipient =
        form.watch("recipient_user_ids").length > 0 ||
        form.watch("recipient_group_ids").length > 0 ||
        form.watch("recipient_resolver_key") !== NONE;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{rule ? "Edit rule" : "New rule"}</DialogTitle>
                    <DialogDescription>
                        Rules fire for events in your tenant and turn into emails or in-app
                        notifications for the people you choose.
                    </DialogDescription>
                </DialogHeader>

                <Form {...form}>
                    <form
                        onSubmit={form.handleSubmit((v) => saveMutation.mutate(v))}
                        className="space-y-5"
                    >
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Name</FormLabel>
                                    <FormControl>
                                        <Input
                                            {...field}
                                            placeholder="e.g. QA supervisor on any failure"
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="description"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Description</FormLabel>
                                    <FormControl>
                                        <Textarea
                                            rows={2}
                                            {...field}
                                            placeholder="Optional — explain what this rule does for your team."
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="event_type"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Event</FormLabel>
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {catalog.map((ev) => (
                                                <SelectItem key={ev.key} value={ev.key}>
                                                    {ev.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {selectedEvent && (
                                        <FormDescription>
                                            {selectedEvent.description}
                                        </FormDescription>
                                    )}
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="scope_mode"
                            render={({ field }) => (
                                <FormItem className="space-y-2">
                                    <FormLabel>Applies to</FormLabel>
                                    <FormControl>
                                        <RadioGroup
                                            value={field.value}
                                            onValueChange={field.onChange}
                                            className="flex flex-col gap-2"
                                        >
                                            <Label className="flex items-center gap-2 cursor-pointer font-normal">
                                                <RadioGroupItem value="any" />
                                                All occurrences tenant-wide
                                            </Label>
                                            {selectedEvent?.scope_model && (
                                                <Label className="flex items-center gap-2 cursor-pointer font-normal">
                                                    <RadioGroupItem value="specific" />
                                                    A specific{" "}
                                                    {selectedEvent.scope_label ?? "object"}
                                                </Label>
                                            )}
                                        </RadioGroup>
                                    </FormControl>
                                </FormItem>
                            )}
                        />

                        {scopeMode === "specific" &&
                            selectedEvent?.scope_model === "Tracker.Steps" && (
                                <FormField
                                    control={form.control}
                                    name="scope_object_id"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>{selectedEvent.scope_label}</FormLabel>
                                            <Select
                                                value={field.value || ""}
                                                onValueChange={field.onChange}
                                            >
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Choose a step…" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {stepList.map((s) => (
                                                        <SelectItem key={s.id} value={s.id}>
                                                            {s.name}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            )}

                        <FormField
                            control={form.control}
                            name="channel_type"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Channel</FormLabel>
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="EMAIL">Email</SelectItem>
                                            <SelectItem value="IN_APP">In-App</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </FormItem>
                            )}
                        />

                        {/* Recipients */}
                        <div className="space-y-2">
                            <Label>Recipients</Label>
                            <div className="text-xs text-muted-foreground">
                                Anyone matched by any of these will be notified. At least one
                                source is required.
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <Label className="text-xs">Users</Label>
                                    <MultiCheckboxList
                                        items={employeeList.map((u: any) => ({
                                            id: u.id,
                                            label:
                                                u.full_name ||
                                                `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim() ||
                                                u.email ||
                                                `User ${u.id}`,
                                        }))}
                                        selected={form.watch("recipient_user_ids")}
                                        onChange={(ids) =>
                                            form.setValue("recipient_user_ids", ids as number[])
                                        }
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">Groups</Label>
                                    <MultiCheckboxList
                                        items={groupList.map((g) => ({
                                            id: g.id,
                                            label: g.name,
                                        }))}
                                        selected={form.watch("recipient_group_ids")}
                                        onChange={(ids) =>
                                            form.setValue("recipient_group_ids", ids as string[])
                                        }
                                    />
                                </div>
                            </div>

                            <FormField
                                control={form.control}
                                name="recipient_resolver_key"
                                render={({ field }) => (
                                    <FormItem>
                                        <Label className="text-xs">Role-based</Label>
                                        <Select
                                            value={field.value}
                                            onValueChange={field.onChange}
                                        >
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value={NONE}>(none)</SelectItem>
                                                {(selectedEvent?.resolver_keys ?? []).map((k) => (
                                                    <SelectItem key={k} value={k}>
                                                        {humanizeKey(k)}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormDescription>
                                            Resolved at the moment of the event. E.g.
                                            &quot;operator assigned to the step&quot;.
                                        </FormDescription>
                                    </FormItem>
                                )}
                            />

                            {!hasRecipient && (
                                <div className="text-xs text-destructive">
                                    Pick at least one user, group, or role resolver.
                                </div>
                            )}
                        </div>

                        <FormField
                            control={form.control}
                            name="cooldown_minutes"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Cooldown (minutes)</FormLabel>
                                    <FormControl>
                                        <Input type="number" min={0} {...field} />
                                    </FormControl>
                                    <FormDescription>
                                        Minimum gap between notifications to the same recipient
                                        from this rule. 0 disables dedup.
                                    </FormDescription>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="is_active"
                            render={({ field }) => (
                                <FormItem className="flex items-center justify-between">
                                    <div>
                                        <FormLabel>Active</FormLabel>
                                        <FormDescription>
                                            Paused rules don&apos;t fire, but history is kept.
                                        </FormDescription>
                                    </div>
                                    <FormControl>
                                        <Switch
                                            checked={field.value}
                                            onCheckedChange={field.onChange}
                                        />
                                    </FormControl>
                                </FormItem>
                            )}
                        />

                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => onOpenChange(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={!hasRecipient || saveMutation.isPending}
                            >
                                {saveMutation.isPending ? "Saving…" : rule ? "Save" : "Create"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ruleToForm(rule: NotificationRule): FormValues {
    return {
        name: rule.name,
        description: rule.description ?? "",
        event_type: rule.event_type,
        channel_type: (rule.channel_type ?? "EMAIL") as "EMAIL" | "IN_APP",
        scope_mode: rule.scope_object_id ? "specific" : "any",
        scope_object_id: rule.scope_object_id ?? "",
        recipient_user_ids: (rule.recipient_users ?? []) as number[],
        recipient_group_ids: (rule.recipient_groups ?? []) as string[],
        recipient_resolver_key: rule.recipient_resolver_key || NONE,
        cooldown_minutes: Math.round((rule.min_gap_seconds ?? 3600) / 60),
        is_active: rule.is_active ?? true,
    };
}

function formatCooldown(seconds: number): string {
    if (seconds === 0) return "none";
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.round(seconds / 60);
    if (mins < 60) return `${mins}m`;
    const hours = Math.round(mins / 60);
    return `${hours}h`;
}

function humanizeKey(key: string): string {
    return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function MultiCheckboxList<T extends string | number>({
    items,
    selected,
    onChange,
}: {
    items: Array<{ id: T; label: string }>;
    selected: T[];
    onChange: (ids: T[]) => void;
}) {
    const selectedSet = new Set(selected);
    const toggle = (id: T) => {
        if (selectedSet.has(id)) {
            onChange(selected.filter((x) => x !== id));
        } else {
            onChange([...selected, id]);
        }
    };
    return (
        <ScrollArea className="h-40 rounded-md border">
            <div className="p-2 space-y-1">
                {items.length === 0 ? (
                    <div className="text-xs text-muted-foreground p-2">(none available)</div>
                ) : (
                    items.map((item) => (
                        <label
                            key={String(item.id)}
                            className="flex items-center gap-2 text-sm cursor-pointer py-1 px-1 rounded hover:bg-muted"
                        >
                            <Checkbox
                                checked={selectedSet.has(item.id)}
                                onCheckedChange={() => toggle(item.id)}
                            />
                            <span>{item.label}</span>
                        </label>
                    ))
                )}
            </div>
        </ScrollArea>
    );
}
