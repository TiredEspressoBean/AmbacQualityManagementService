// "Why isn't this on the board?" — the work the Gantt can't show.
//
// The Gantt renders what the solver placed; it is silent about what the solver never
// saw, and that silence is where planner time goes. This panel closes the loop: every
// work order with open units the active schedule doesn't fully cover, grouped by the
// single most actionable reason, each row carrying the fix.
//
// Reasons come from the backend already resolved and ranked (see
// services/scheduling/diagnostics.py) — this component only presents them.
import { AlertTriangle, CheckCircle2, RotateCw } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUnscheduled, type UnscheduledReason, type UnscheduledRow } from "@/hooks/useScheduling";

// Severity drives the accent only — the ordering itself is the backend's.
const TONE: Record<UnscheduledReason, string> = {
  on_hold: "border-l-amber-500",
  no_process: "border-l-red-500",
  no_open_units: "border-l-muted-foreground/40",
  no_routing: "border-l-red-500",
  no_timings: "border-l-red-500",
  unstaffable: "border-l-red-500",
  outside_horizon: "border-l-sky-500",
  material_gated: "border-l-amber-500",
  material_short: "border-l-amber-500",
  stale_schedule: "border-l-sky-500",
  not_solved: "border-l-sky-500",
};

/** "2026-10-08" → "Oct 8" — the board's own date register, not an ISO stamp. */
const shortDate = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

type Props = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onOpenWorkOrder?: (workOrderId: string) => void;
};

export function UnscheduledPanel({ open, onOpenChange, onOpenWorkOrder }: Props) {
  const { data, isLoading, isError, refetch, isFetching } = useUnscheduled(open);

  // Preserve the backend's fix-this-first ranking while grouping by reason: walk the
  // already-sorted rows and open a new group each time the reason changes.
  const groups: { reason: UnscheduledReason; label: string; rows: UnscheduledRow[] }[] = [];
  for (const row of data?.work_orders ?? []) {
    const last = groups[groups.length - 1];
    if (last && last.reason === row.reason) last.rows.push(row);
    else groups.push({ reason: row.reason, label: row.reason_label, rows: [row] });
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b px-5 py-4">
          <SheetTitle className="flex items-center gap-2">
            Why isn&rsquo;t this scheduled?
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto h-7 w-7"
              title="Re-check"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RotateCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            </Button>
          </SheetTitle>
          <SheetDescription>
            {data
              ? `${data.unscheduled_work_orders} of ${data.open_work_orders} open work order(s) aren't fully on the board.`
              : "Open work the active schedule doesn't cover."}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1">
          <div className="space-y-5 px-5 py-4">
            {isLoading && (
              <p className="text-sm text-muted-foreground">Checking the schedule…</p>
            )}

            {isError && (
              <div className="space-y-2 text-sm">
                <p className="text-destructive">Couldn&rsquo;t run the check.</p>
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  Try again
                </Button>
              </div>
            )}

            {data && groups.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                <p className="text-sm font-medium">Everything open is on the board.</p>
                <p className="text-xs text-muted-foreground">
                  All {data.open_units} open unit(s) across {data.open_work_orders} work
                  order(s) have scheduled tasks.
                </p>
              </div>
            )}

            {data?.is_stale && groups.length > 0 && (
              <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-xs">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                <span>
                  The active schedule is stale — some of these may resolve on the next
                  solve.
                </span>
              </div>
            )}

            {groups.map((g) => (
              <section key={g.reason} className="space-y-2">
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {g.label}
                  <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                    {g.rows.length}
                  </Badge>
                </h3>
                {g.rows.map((r) => (
                  <button
                    key={r.work_order_id}
                    type="button"
                    disabled={!onOpenWorkOrder}
                    onClick={() => onOpenWorkOrder?.(r.work_order_id)}
                    className={`w-full rounded-md border border-l-4 ${TONE[r.reason]} bg-card p-3 text-left transition-colors enabled:hover:bg-accent/40 disabled:cursor-default`}
                  >
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-sm font-medium">{r.erp_id}</span>
                      {r.part_type && (
                        <span className="truncate text-xs text-muted-foreground">
                          {r.part_type}
                        </span>
                      )}
                      {/* 0 of 0 placed is a tautology on an order with nothing left
                          to work — the detail line already says so. */}
                      {r.open_units > 0 && (
                        <span className="ml-auto shrink-0 text-xs tabular-nums text-muted-foreground">
                          {r.scheduled_units}/{r.open_units} placed
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-xs">{r.detail}</p>
                    <p className="mt-1 text-xs text-muted-foreground">→ {r.fix}</p>
                    {r.due_date && (
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Due {shortDate(r.due_date)}
                      </p>
                    )}
                  </button>
                ))}
              </section>
            ))}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
