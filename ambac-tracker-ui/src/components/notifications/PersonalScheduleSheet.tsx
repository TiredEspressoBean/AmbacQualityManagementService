/**
 * "Schedule a digest" — the customer-facing surface for personal scheduled
 * deliveries. No scope picker (always personal), no recipient picker (owner
 * is implicit), no provider params (auto-merged from owner's context where
 * applicable).
 *
 *   [Report ▾]
 *   Cadence: Weekly / Monthly
 *   Day of week (or month)
 *   Time of day
 *   Timezone
 *   Email (always on)
 *   [Subscribe]
 *
 * Saves a personal NotificationSchedule via the API.
 */
import { useEffect, useMemo, useState } from "react";
import { CalendarClock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
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

import {
    useCreatePersonalSchedule,
    useScheduledContentProviders,
    useUpdatePersonalSchedule,
    type PersonalSchedule,
} from "@/hooks/notificationSchedules";

const DAYS_OF_WEEK = [
    { value: 0, label: "Monday" },
    { value: 1, label: "Tuesday" },
    { value: 2, label: "Wednesday" },
    { value: 3, label: "Thursday" },
    { value: 4, label: "Friday" },
    { value: 5, label: "Saturday" },
    { value: 6, label: "Sunday" },
];

const COMMON_TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Tokyo",
];

type Cadence = "weekly" | "monthly";

interface FormState {
    name: string;
    providerKind: string;
    cadence: Cadence;
    dayOfWeek: number;
    dayOfMonth: number;
    timeOfDay: string;  // "HH:MM"
    timezone: string;
}

function freshForm(defaultProviderKind: string): FormState {
    return {
        name: "Weekly order summary",
        providerKind: defaultProviderKind,
        cadence: "weekly",
        dayOfWeek: 4,  // Friday default
        dayOfMonth: 1,
        timeOfDay: "08:00",
        timezone: "UTC",
    };
}

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    editingSchedule?: PersonalSchedule | null;
}

export function PersonalScheduleSheet({
    open,
    onOpenChange,
    editingSchedule = null,
}: Props) {
    const { data: providers } = useScheduledContentProviders();
    const createSchedule = useCreatePersonalSchedule();
    const updateSchedule = useUpdatePersonalSchedule();
    const saving = createSchedule.isPending || updateSchedule.isPending;

    const defaultProvider = providers?.[0]?.name ?? "customer_active_orders";
    const [form, setForm] = useState<FormState>(() => freshForm(defaultProvider));

    useEffect(() => {
        if (!open) return;
        if (editingSchedule) {
            setForm({
                name: editingSchedule.name,
                providerKind: editingSchedule.provider_kind ?? defaultProvider,
                cadence: (editingSchedule.cadence as Cadence) ?? "weekly",
                dayOfWeek: editingSchedule.day_of_week ?? 4,
                dayOfMonth: editingSchedule.day_of_month ?? 1,
                timeOfDay: (editingSchedule.time_of_day ?? "08:00:00").slice(0, 5),
                timezone: editingSchedule.timezone ?? "UTC",
            });
        } else {
            setForm(freshForm(defaultProvider));
        }
    }, [open, editingSchedule, defaultProvider]);

    const currentProvider = useMemo(
        () => (providers ?? []).find((p) => p.name === form.providerKind),
        [providers, form.providerKind],
    );

    const patch = (u: Partial<FormState>) => setForm((curr) => ({ ...curr, ...u }));

    const handleSave = () => {
        const close = () => onOpenChange(false);
        const wirePayload = {
            name: form.name.trim() || "Scheduled digest",
            provider_kind: form.providerKind,
            cadence: form.cadence,
            day_of_week: form.cadence === "weekly" ? form.dayOfWeek : null,
            day_of_month: form.cadence === "monthly" ? form.dayOfMonth : null,
            time_of_day: `${form.timeOfDay}:00`,
            timezone: form.timezone,
            channels: ["email"],
            enabled: true,
        };
        if (editingSchedule) {
            updateSchedule.mutate(
                { id: editingSchedule.id, data: wirePayload },
                { onSuccess: close },
            );
        } else {
            createSchedule.mutate(wirePayload, { onSuccess: close });
        }
    };

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
                <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                        <CalendarClock className="h-5 w-5 text-primary" />
                        {editingSchedule ? "Edit digest" : "Schedule a digest"}
                    </SheetTitle>
                    <SheetDescription>
                        A recurring summary delivered to your email on the cadence you choose.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-5 px-4">
                    <div className="space-y-2">
                        <Label>Name</Label>
                        <Input
                            value={form.name}
                            onChange={(e) => patch({ name: e.target.value })}
                            placeholder="e.g. Weekly order summary"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Report</Label>
                        <Select
                            value={form.providerKind}
                            onValueChange={(v) => patch({ providerKind: v })}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {(providers ?? []).map((p) => (
                                    <SelectItem key={p.name} value={p.name}>
                                        {p.title}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {currentProvider && (
                            <p className="text-xs text-muted-foreground">
                                {currentProvider.description}
                            </p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label>Cadence</Label>
                        <RadioGroup
                            value={form.cadence}
                            onValueChange={(v) => patch({ cadence: v as Cadence })}
                            className="flex gap-3"
                        >
                            <label className="flex items-center gap-2 cursor-pointer rounded-md border px-3 py-1.5 text-sm has-[input:checked]:border-primary has-[input:checked]:bg-primary/5">
                                <RadioGroupItem value="weekly" />
                                Weekly
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer rounded-md border px-3 py-1.5 text-sm has-[input:checked]:border-primary has-[input:checked]:bg-primary/5">
                                <RadioGroupItem value="monthly" />
                                Monthly
                            </label>
                        </RadioGroup>
                    </div>

                    {form.cadence === "weekly" ? (
                        <div className="space-y-2">
                            <Label>Day of week</Label>
                            <Select
                                value={String(form.dayOfWeek)}
                                onValueChange={(v) => patch({ dayOfWeek: Number(v) })}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {DAYS_OF_WEEK.map((d) => (
                                        <SelectItem key={d.value} value={String(d.value)}>
                                            {d.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <Label>Day of month</Label>
                            <Input
                                type="number"
                                min={1}
                                max={28}
                                value={form.dayOfMonth}
                                onChange={(e) =>
                                    patch({
                                        dayOfMonth: Math.min(28, Math.max(1, Number(e.target.value) || 1)),
                                    })
                                }
                            />
                            <p className="text-[11px] text-muted-foreground">1–28.</p>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label>Time of day</Label>
                        <Input
                            type="time"
                            value={form.timeOfDay}
                            onChange={(e) => patch({ timeOfDay: e.target.value })}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Timezone</Label>
                        <Select
                            value={form.timezone}
                            onValueChange={(v) => patch({ timezone: v })}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {COMMON_TIMEZONES.map((tz) => (
                                    <SelectItem key={tz} value={tz}>
                                        {tz}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <SheetFooter className="flex-row gap-2">
                    <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button className="flex-1" onClick={handleSave} disabled={saving}>
                        {editingSchedule ? "Save" : "Schedule"}
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
