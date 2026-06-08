import { AlertTriangle, Bell, Info, Shield } from "lucide-react";

export type CalloutVariant = "caution" | "note" | "reminder" | "safety";

export const CALLOUT_CONFIG: Record<
    CalloutVariant,
    { label: string; icon: React.ComponentType<{ className?: string }>; cls: string }
> = {
    caution: { label: "Caution", icon: AlertTriangle, cls: "border-amber-500/40 bg-amber-50/40 dark:bg-amber-950/20" },
    note: { label: "Note", icon: Info, cls: "border-blue-500/40 bg-blue-50/40 dark:bg-blue-950/20" },
    reminder: { label: "Reminder", icon: Bell, cls: "border-purple-500/40 bg-purple-50/40 dark:bg-purple-950/20" },
    safety: { label: "Safety", icon: Shield, cls: "border-red-500/40 bg-red-50/40 dark:bg-red-950/20" },
};
