import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

import type { ScheduleCadence, ScheduleDraft } from "@/lib/notifications/scheduleDraft";

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

export function ScheduleCard({
    draft,
    patch,
}: {
    draft: ScheduleDraft;
    patch: (u: Partial<ScheduleDraft>) => void;
}) {
    const onCadenceChange = (next: ScheduleCadence) => {
        patch({
            cadence: next,
            dayOfWeek: next === "weekly" ? draft.dayOfWeek ?? 0 : null,
            dayOfMonth: next === "monthly" ? draft.dayOfMonth ?? 1 : null,
        });
    };

    // `time_of_day` ships as HH:MM:SS over the wire; the HTML <input type=time>
    // emits HH:MM. Normalize.
    const timeForInput = draft.timeOfDay.slice(0, 5);
    const onTimeChange = (v: string) => patch({ timeOfDay: `${v}:00` });

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Schedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Cadence</Label>
                    <RadioGroup
                        value={draft.cadence}
                        onValueChange={(v) => onCadenceChange(v as ScheduleCadence)}
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

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {draft.cadence === "weekly" ? (
                        <div className="space-y-2">
                            <Label>Day of week</Label>
                            <Select
                                value={String(draft.dayOfWeek ?? 0)}
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
                                value={draft.dayOfMonth ?? 1}
                                onChange={(e) =>
                                    patch({ dayOfMonth: Math.min(28, Math.max(1, Number(e.target.value) || 1)) })
                                }
                            />
                            <p className="text-[11px] text-muted-foreground">
                                1–28 (avoids February gotchas).
                            </p>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label>Time of day</Label>
                        <Input
                            type="time"
                            value={timeForInput}
                            onChange={(e) => onTimeChange(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Timezone</Label>
                        <Select
                            value={draft.timezone}
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
                        <p className="text-[11px] text-muted-foreground">
                            Wall-clock local time. UTC fire shifts ±1h on DST transitions.
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
