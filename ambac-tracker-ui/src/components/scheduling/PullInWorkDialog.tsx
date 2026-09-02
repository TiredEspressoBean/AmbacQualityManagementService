// "Pull in work" — the planner's release queue, on the board they already live on.
//
// Under manual release mode the primary planning act isn't *creating* a work order,
// it's deciding which of the ones that already exist go on the schedule. A bigger ERP
// would put this on its own workbench page; at 50-500 people the planner and the
// scheduler are the same person looking at the same screen, so the queue belongs here.
//
// Creating a work order stays available as the secondary, rush-order path.
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Plus } from "lucide-react";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useReleaseQueue, useBulkRelease, type ReleaseQueueRow,
} from "@/hooks/useScheduling";

/** Utilisation → tone. Banded, not a gradient: the planner's decision changes at
 *  "room / tight / over", and a smooth ramp makes 88% and 104% look alike. */
const loadTone = (u: number) =>
  u > 1 ? "text-red-600 dark:text-red-400"
    : u > 0.85 ? "text-amber-700 dark:text-amber-400"
      : "text-muted-foreground";

const shortDate = (iso: string | null) => {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const PRIORITY: Record<number, string> = {
  1: "Urgent", 2: "High", 3: "Normal", 4: "Low",
};

type Props = {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onNewWorkOrder: () => void;
};

export function PullInWorkDialog({ open, onOpenChange, onNewWorkOrder }: Props) {
  const { data, isLoading } = useReleaseQueue(open);
  const rec = data?.recommendation;
  const bulkRelease = useBulkRelease();


  // Memoised: `rows` feeds an effect and two memos, and a fresh [] each render
  // would re-run all three every time.
  const rows = useMemo(() => data?.work_orders ?? [], [data]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [overrideReason, setOverrideReason] = useState("");

  // Drop selections for rows that left the queue (released elsewhere, or closed) so
  // the count never claims more than it can act on.
  useEffect(() => {
    setSelected((prev) => {
      const live = new Set(rows.map((r) => r.id));
      const next = new Set([...prev].filter((id) => live.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [rows]);

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  // Live load: committed hours plus whatever is currently ticked. This is the whole
  // point of the panel — a planner ticking 13 orders otherwise has no idea whether
  // that's a comfortable week or three times capacity.
  const projected = useMemo(() => {
    if (!rec) return [];
    const added: Record<string, number> = {};
    for (const d of rec.decisions) {
      if (!selected.has(d.work_order_id)) continue;
      for (const [name, h] of Object.entries(d.hours)) {
        added[name] = (added[name] ?? 0) + h;
      }
    }
    return rec.resources
      .filter((r) => r.norm_hours > 0)
      .map((r) => {
        const projected_hours = r.committed_hours + (added[r.name] ?? 0);
        return { ...r, projected_hours, util: projected_hours / r.norm_hours };
      })
      .sort((a, b) => b.util - a.util);
  }, [rec, selected]);

  const readyRows = useMemo(() => rows.filter((r) => r.ready), [rows]);
  const recommendedIds = useMemo(
    () => (rec?.decisions ?? []).filter((d) => d.release).map((d) => d.work_order_id),
    [rec]);
  const selectedRows = useMemo(
    () => rows.filter((r) => selected.has(r.id)), [rows, selected]);
  const blockedSelected = selectedRows.filter((r) => !r.ready);
  const needsReason = blockedSelected.length > 0 && overrideReason.trim() === "";

  const submit = () => {
    if (!selected.size) return;
    bulkRelease.mutate(
      { ids: [...selected], override_reason: overrideReason.trim() },
      {
        onSuccess: () => {
          setSelected(new Set());
          setOverrideReason("");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Pull in work</DialogTitle>
          <DialogDescription>
            Work orders waiting to be released onto the schedule. Releasing doesn&rsquo;t
            move anything by itself — re-solve to plan the released work.
          </DialogDescription>
        </DialogHeader>

        <div className="flex shrink-0 items-center gap-2 border-b pb-2 text-sm">
          {/* The recommendation is advisory — it pre-selects, it doesn't release.
              "Select all ready" stays, because a planner overriding the norms is a
              legitimate act, not an error. */}
          {recommendedIds.length > 0 && (
            <Button
              variant="secondary" size="sm"
              onClick={() => setSelected(new Set(recommendedIds))}
              title={rec?.policy_label}
            >
              Recommend ({recommendedIds.length})
            </Button>
          )}
          <Button
            variant="ghost" size="sm"
            onClick={() => setSelected(new Set(readyRows.map((r) => r.id)))}
            disabled={!readyRows.length}
          >
            Select all ready ({readyRows.length})
          </Button>
          <Button
            variant="ghost" size="sm"
            onClick={() => setSelected(new Set())}
            disabled={!selected.size}
          >
            Clear
          </Button>
          <Button variant="outline" size="sm" className="ml-auto" onClick={onNewWorkOrder}>
            <Plus className="mr-1 h-4 w-4" /> New work order
          </Button>
        </div>

        {/* A native scroll container, not Radix ScrollArea: its viewport is sized
            `h-full`, which needs a DEFINITE parent height — `max-height` doesn't
            provide one, so the viewport grows to its content and (the root not
            clipping) the list escapes the dialog over the footer. `min-h-0` is the
            other half: a flex child defaults to min-height:auto and won't shrink. */}
        <div className="-mx-6 min-h-0 flex-1 overflow-y-auto px-6">
          <div className="space-y-2 py-2">
            {isLoading && (
              <p className="text-sm text-muted-foreground">Loading the queue…</p>
            )}

            {!isLoading && !rows.length && (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                <p className="text-sm font-medium">Nothing waiting to be released.</p>
                <p className="text-xs text-muted-foreground">
                  Every open work order is already authorized for scheduling.
                </p>
              </div>
            )}

            {rows.map((r: ReleaseQueueRow) => (
              <label
                key={r.id}
                className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors hover:bg-accent/40 ${
                  selected.has(r.id) ? "border-primary/60 bg-accent/30" : ""
                }`}
              >
                <Checkbox
                  className="mt-0.5"
                  checked={selected.has(r.id)}
                  onCheckedChange={() => toggle(r.id)}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="font-mono text-sm font-medium">{r.erp_id}</span>
                    {r.part_type && (
                      <span className="truncate text-xs text-muted-foreground">
                        {r.part_type}
                      </span>
                    )}
                    {r.priority <= 2 && (
                      <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                        {PRIORITY[r.priority] ?? r.priority}
                      </Badge>
                    )}
                    <span className="ml-auto shrink-0 text-xs tabular-nums text-muted-foreground">
                      {r.open_units} unit{r.open_units === 1 ? "" : "s"} · due{" "}
                      {shortDate(r.due_date)}
                    </span>
                  </div>

                  {r.blockers.map((b) => (
                    <p key={b.code} className="mt-1 text-xs text-red-600 dark:text-red-400">
                      ✕ {b.detail}
                    </p>
                  ))}
                  {r.warnings.map((w) => (
                    <p key={w.code} className="mt-1 text-xs text-amber-700 dark:text-amber-400">
                      ! {w.detail}
                    </p>
                  ))}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Blocked rows don't disappear from the queue — a planner who knows the
            shortage is covered must be able to take them, on the record. */}
        {blockedSelected.length > 0 && (
          <div className="grid gap-1 border-t pt-3">
            <Label className="flex items-center gap-1.5 text-xs">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
              {blockedSelected.length} selected order(s) aren&rsquo;t ready — reason for
              releasing anyway
            </Label>
            <Input
              value={overrideReason}
              placeholder="e.g. routing lands Thursday"
              onChange={(e) => setOverrideReason(e.target.value)}
            />
          </div>
        )}

        {/* Load if you released what's ticked. Only the tightest few — a planner
            needs to know what's about to break, not read a full census. */}
        {projected.length > 0 && (
          <div className="shrink-0 space-y-1 border-t pt-3 text-xs">
            <div className="flex items-baseline justify-between">
              <span className="font-medium">
                Load if released · next {rec?.window_days}d
              </span>
              <span className="text-muted-foreground">
                {rec?.policy_label} @ {rec?.norm_pct}%
              </span>
            </div>
            {projected.slice(0, 4).map((r) => (
              <div key={r.name} className="flex items-baseline justify-between gap-2">
                <span className="truncate text-muted-foreground">{r.name}</span>
                <span className={`shrink-0 tabular-nums ${loadTone(r.util)}`}>
                  {r.projected_hours.toFixed(0)} / {r.norm_hours.toFixed(0)}h
                  {" · "}{Math.round(r.util * 100)}%
                </span>
              </div>
            ))}
          </div>
        )}

        <DialogFooter className="shrink-0 gap-2 border-t bg-background pt-3 sm:justify-between">
          <span className="self-center text-xs text-muted-foreground">
            {selected.size} selected
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            <Button
              onClick={submit}
              disabled={!selected.size || needsReason || bulkRelease.isPending}
            >
              {bulkRelease.isPending
                ? "Releasing…"
                : `Release ${selected.size || ""}`.trim()}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
