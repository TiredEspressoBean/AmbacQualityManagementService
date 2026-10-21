/** Shared pieces of Production › Orders: the projection line, blocker chips and the
 *  progress bar. */
import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { parseDateOnly } from "@/lib/date-only";
import type { OrderBlocker, OrderBookRow } from "@/hooks/useOrderBook";

type Projection = OrderBookRow["projection"];
type Progress = OrderBookRow["progress"];

const fmt = (d: string | null | undefined) =>
    d ? parseDateOnly(d).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : null;

/** "Due Nov 11 · projected Nov 14 · 3 d late" / "· on track" / "· not scheduled". */
export function ProjectionText({ p }: { p: Projection }) {
    const due = fmt(p.due);
    const projected = fmt(p.projected);
    return (
        <span className="whitespace-nowrap text-sm">
            {due ? `Due ${due}` : "No due date"}
            {p.state === "late" && (
                <span className="font-medium text-destructive">
                    {projected ? ` · projected ${projected}` : ""} · {p.slip_days ?? "?"} d late
                </span>
            )}
            {p.state === "on_track" && (
                <span className="text-green-600 dark:text-green-400">
                    {projected ? ` · projected ${projected}` : ""} · on track
                </span>
            )}
            {p.state === "not_scheduled" && (
                <span className="text-amber-600 dark:text-amber-400">
                    {projected ? ` · projected ${projected} (part)` : ""} · not scheduled
                </span>
            )}
        </span>
    );
}

export function BlockerChips({ blockers, more = 0 }: { blockers: readonly OrderBlocker[]; more?: number }) {
    if (blockers.length === 0) return <span className="text-xs text-muted-foreground">—</span>;
    return (
        <span className="flex flex-wrap gap-1">
            {blockers.map((b, i) => (
                <Link key={`${b.kind}-${i}`} to={b.link} onClick={(e) => e.stopPropagation()}>
                    <Badge variant="outline"
                           className={b.kind === "on_hold" || b.kind === "quarantined"
                               ? "border-destructive/50 text-destructive" : "border-amber-500/50 text-amber-700 dark:text-amber-400"}>
                        {b.label}
                    </Badge>
                </Link>
            ))}
            {more > 0 && <Badge variant="secondary">+{more}</Badge>}
        </span>
    );
}

/** Ordered → planned → in work → done → shipped, as one stacked bar. */
export function ProgressBar({ p }: { p: Progress }) {
    const total = Math.max(p.ordered, p.planned, 1);
    const notStarted = Math.max(0, p.planned - p.in_work - p.done - p.shipped);
    const unplanned = Math.max(0, p.ordered - p.planned);
    const seg = (n: number, cls: string) =>
        n > 0 ? <div className={cls} style={{ width: `${(n / total) * 100}%` }} /> : null;
    const title = `Ordered ${p.ordered} · planned ${p.planned} · in work ${p.in_work} · done ${p.done} · shipped ${p.shipped}`;
    return (
        <div className="w-36" title={title} aria-label={title}>
            <div className="flex h-2 overflow-hidden rounded bg-muted">
                {seg(p.shipped, "bg-green-600")}
                {seg(p.done, "bg-green-400")}
                {seg(p.in_work, "bg-sky-500")}
                {seg(notStarted, "bg-muted-foreground/30")}
                {seg(unplanned, "bg-amber-400/40")}
            </div>
            <div className="mt-0.5 text-[10px] tabular-nums text-muted-foreground">
                {p.shipped}/{p.ordered} shipped
            </div>
        </div>
    );
}
