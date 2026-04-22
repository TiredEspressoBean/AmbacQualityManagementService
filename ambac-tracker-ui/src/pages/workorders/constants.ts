// Shared constants for WorkOrder pages.
//
// Color policy: use shadcn theme tokens only (primary, secondary, muted,
// destructive, accent, foreground). No hand-tuned tailwind-700/dark-300
// pairs. Distinguishing tones come from opacity variants of the same
// semantic tokens. If we need more vocabulary later, add named CSS
// variables to `src/index.css`.

export const WO_PRIORITY_LABELS: Record<
    number,
    { label: string; className: string }
> = {
    1: { label: "Urgent", className: "bg-destructive text-destructive-foreground" },
    2: { label: "High", className: "bg-destructive/60 text-destructive-foreground" },
    3: { label: "Normal", className: "bg-secondary text-secondary-foreground" },
    4: { label: "Low", className: "bg-muted text-muted-foreground" },
};

// Bar-fill colors for the per-step status composition bar. Theme tokens
// with opacity variants only — the palette collapses to primary (positive
// work) + destructive (problems) + muted/secondary (inactive), which is
// honest to the theme and still reads cleanly.
export const STATUS_BAR_FILL: Record<string, string> = {
    COMPLETED: "bg-primary",
    READY_FOR_NEXT_STEP: "bg-primary",
    IN_PROGRESS: "bg-primary/60",
    AWAITING_QA: "bg-secondary",
    PENDING: "bg-muted",
    REWORK_NEEDED: "bg-destructive/50",
    REWORK_IN_PROGRESS: "bg-destructive/50",
    QUARANTINED: "bg-destructive",
    SCRAPPED: "bg-foreground/30",
};

export const HOLD_REASONS = [
    { value: "MATERIAL", label: "Waiting on material" },
    { value: "QUALITY", label: "Quality hold" },
    { value: "TOOLING", label: "Tooling / fixture" },
    { value: "OPERATOR", label: "Operator unavailable" },
    { value: "CUSTOMER", label: "Customer hold" },
    { value: "OTHER", label: "Other" },
] as const;

export type HoldReason = typeof HOLD_REASONS[number]["value"];
