/**
 * A step's measured setup / cycle beside the authored value: what the step records
 * say it takes, how much history that rests on, and which one the scheduler uses.
 * Measured values are never applied on their own — "Use measured" is an edit.
 */
import { Badge } from "@/components/ui/badge";
import type { MeasuredStepTiming } from "@/hooks/useSchedulingSetup";

export type Aspect = "setup" | "cycle";

/** The measured value for an aspect, or null when the records don't give one. */
export function measuredValue(m: MeasuredStepTiming | undefined, aspect: Aspect): number | null {
    if (!m) return null;
    if (aspect === "setup") return m.cycle_per_load_minutes == null ? m.setup_minutes ?? null : null;
    return m.cycle_per_load_minutes ?? m.per_piece_minutes ?? null;
}

const SOURCE_LABEL: Record<string, string> = {
    authored: "Using authored",
    measured: "Using measured",
    expected: "Using the step's expected duration",
    none: "Not set",
};

export function SourceBadge({ source }: { source: string | undefined }) {
    if (!source) return null;
    return (
        <Badge variant={source === "authored" ? "secondary" : "outline"} className="text-[10px] font-normal">
            {SOURCE_LABEL[source] ?? source}
        </Badge>
    );
}

/** "measured 27 min · 34 runs", or why there isn't a measurement. */
export function MeasuredLine({ m, aspect }: { m: MeasuredStepTiming | undefined; aspect: Aspect }) {
    if (!m) return <span className="text-xs text-muted-foreground">No runs recorded</span>;
    const value = measuredValue(m, aspect);
    const drift = aspect === "setup" ? m.setup_drift : m.cycle_drift;
    const perLoad = aspect === "cycle" && m.cycle_per_load_minutes != null;
    const basis = perLoad
        ? `${m.loads} load${m.loads === 1 ? "" : "s"}`
        : `${m.runs} run${m.runs === 1 ? "" : "s"}`;
    if (value == null) {
        const why = aspect === "setup" && m.method === "average"
            ? "not separated from per-piece time"
            : `not enough runs yet`;
        return (
            <span className="text-xs text-muted-foreground" title={m.note || undefined}>
                measured: {why} · {basis}
            </span>
        );
    }
    return (
        <span className="inline-flex flex-wrap items-center gap-1 text-xs text-muted-foreground"
            title={m.note || undefined}>
            measured {value} min{perLoad ? " per load" : aspect === "cycle" ? " per piece" : ""} · {basis}
            {aspect === "cycle" && m.method === "average" && !perLoad && " (average)"}
            {drift && (
                <Badge variant="outline" className="border-amber-500 text-[10px] font-normal text-amber-700 dark:text-amber-400">
                    differs by more than {m.drift_pct}%
                </Badge>
            )}
        </span>
    );
}
