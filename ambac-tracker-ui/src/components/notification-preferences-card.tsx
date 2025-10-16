import {useState} from "react";
import {toast} from "sonner";
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from "@/components/ui/card";
import {Button} from "@/components/ui/button";
import {Loader2} from "lucide-react";
import {useRetrieveNotificationPreferences} from "@/hooks/useRetrieveNotificationPreferences";
import {useCreateNotificationPreference} from "@/hooks/useCreateNotificationPreference";
import {useUpdateNotificationPreference} from "@/hooks/useUpdateNotificationPreference";
import {useDeleteNotificationPreference} from "@/hooks/useDeleteNotificationPreference";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {Label} from "@/components/ui/label";
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue,} from "@/components/ui/select";
import {Input} from "@/components/ui/input";





const DAYS = [{value: "0", label: "Monday"}, {value: "1", label: "Tuesday"}, {
    value: "2",
    label: "Wednesday"
}, {value: "3", label: "Thursday"}, {value: "4", label: "Friday"}, {value: "5", label: "Saturday"}, {
    value: "6",
    label: "Sunday"
},];

const INTERVALS = [{value: "1", label: "Every week"}, {value: "2", label: "Every 2 weeks"}, {
    value: "4",
    label: "Every 4 weeks"
},];

export function NotificationPreferencesCard() {
    const {data: preferences, isLoading} = useRetrieveNotificationPreferences();
    const createPreference = useCreateNotificationPreference();
    const updatePreference = useUpdateNotificationPreference();
    const deletePreference = useDeleteNotificationPreference();

    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [dayOfWeek, setDayOfWeek] = useState("4");
    const [time, setTime] = useState("15:00");
    const [intervalWeeks, setIntervalWeeks] = useState("1");

    const weeklyReport = preferences?.results.find((p) => p.notification_type === "WEEKLY_REPORT");

    const handleOpen = () => {
        if (weeklyReport) {
            setDayOfWeek(weeklyReport.schedule?.day_of_week?.toString() ?? "4");
            setTime(weeklyReport.schedule?.time ?? "15:00");
            setIntervalWeeks(weeklyReport.schedule?.interval_weeks?.toString() ?? "1");
        }
        setIsDialogOpen(true);
    };

    const handleSave = async () => {
        try {
            const scheduleData = {
                interval_type: "fixed" as const,
                day_of_week: parseInt(dayOfWeek),
                time: time,
                interval_weeks: parseInt(intervalWeeks),
            };

            if (weeklyReport) {
                await updatePreference.mutateAsync({
                    id: weeklyReport.id, data: {schedule: scheduleData},
                });
                toast.success("Updated notification preference");
            } else {
                await createPreference.mutateAsync({
                    notification_type: "WEEKLY_REPORT", channel_type: "email", schedule: scheduleData,
                });
                toast.success("Created notification preference");
            }
            setIsDialogOpen(false);
        } catch {
            toast.error("Failed to save preference");
        }
    };

    const handleDisable = async () => {
        if (!weeklyReport) return;
        try {
            await deletePreference.mutateAsync(weeklyReport.id);
            toast.success("Disabled weekly reports");
            setIsDialogOpen(false);
        } catch {
            toast.error("Failed to disable");
        }
    };

    if (isLoading) {
        return (<Card>
                <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                </CardHeader>
                <CardContent>
                    <Loader2 className="h-6 w-6 animate-spin"/>
                </CardContent>
            </Card>);
    }

    return (<>
            <Card>
                <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                    <CardDescription>Manage your email notifications</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-between">
                        <div className="flex-1">
                            <h4 className="font-medium">Weekly Order Updates</h4>
                            <p className="text-sm text-muted-foreground">
                                {weeklyReport ? (<>
                                        {INTERVALS.find(i => i.value === weeklyReport.schedule?.interval_weeks?.toString())?.label || "Weekly"},{" "}
                                        {DAYS[parseInt(weeklyReport.schedule?.day_of_week?.toString() ?? "4")].label}s
                                        at{" "}
                                        {weeklyReport.schedule?.time}
                                    </>) : ("You are not receiving order updates")}
                            </p>
                        </div>
                        <Button onClick={handleOpen} variant="outline">
                            {weeklyReport ? "Edit" : "Set Up"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Order Report Schedule</DialogTitle>
                        <DialogDescription>
                            Choose when to receive your order updates
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Frequency</Label>
                            <Select value={intervalWeeks} onValueChange={setIntervalWeeks}>
                                <SelectTrigger>
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    {INTERVALS.map((interval) => (
                                        <SelectItem key={interval.value} value={interval.value}>
                                            {interval.label}
                                        </SelectItem>))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Day of Week</Label>
                            <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
                                <SelectTrigger>
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    {DAYS.map((day) => (<SelectItem key={day.value} value={day.value}>
                                            {day.label}
                                        </SelectItem>))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label>Time</Label>
                            <Input type="time" value={time} onChange={(e) => setTime(e.target.value)}
                                   className="bg-background appearance-none [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"/>
                            <p className="text-xs text-muted-foreground">Time is in your local timezone</p>
                        </div>
                    </div>

                    <DialogFooter>
                        {weeklyReport && (<Button
                                variant="destructive"
                                onClick={handleDisable}
                                disabled={deletePreference.isPending}
                            >
                                Disable
                            </Button>)}
                        <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleSave}
                            disabled={createPreference.isPending || updatePreference.isPending}
                        >
                            {createPreference.isPending || updatePreference.isPending ? "Saving..." : "Save"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>);
}
