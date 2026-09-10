/** Rough-cut capacity planning (/production/capacity).
 *
 * The coarse layer above the CP-SAT board. The Gantt answers "what runs Tuesday";
 * this answers "where are we tight in Q2" and "could we take 500 injectors in six
 * months" — questions a 30-day detailed schedule structurally cannot address.
 *
 * Two views on the same arithmetic: a utilization heatmap per resource per month, and
 * an order simulator that adds a hypothetical order to the committed load. Capacity is
 * cumulative in the quote — an order due in March may use every free hour between now
 * and March, so a big order isn't rejected just for exceeding one month.
 */
import { useMemo, useState } from "react";
import { CalendarClock, Gauge, Rocket, Star } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useCapacityLoad, useCapableToPromise, useReleaseForScheduling,
  type CapacityBucket, type PlannedRelease, type ReleaseCheck,
} from "@/hooks/useScheduling";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { downloadCsv } from "@/lib/csv";

const HORIZONS = [6, 12, 24, 36];

/** Utilization → cell colour. Deliberately banded rather than a continuous gradient:
 *  the planner's decision changes at "comfortable / tight / over", and a smooth ramp
 *  makes 88% and 96% look alike when they call for different actions. */
function tone(u: number | null): string {
  if (u == null) return "bg-muted/30 text-muted-foreground";
  if (u >= 1) return "bg-red-500/85 text-white";
  if (u >= 0.85) return "bg-amber-500/80 text-white";
  if (u >= 0.6) return "bg-emerald-500/60 text-emerald-950 dark:text-emerald-50";
  if (u > 0) return "bg-emerald-500/25";
  return "bg-muted/30 text-muted-foreground";
}

const pct = (u: number | null) => (u == null ? "—" : `${Math.round(u * 100)}%`);

/** Material cells carry a quantity, not a ratio — what's LEFT after everything
 *  committed through that month. Banded like the capacity rows so a shortage catches
 *  the eye the same way an overload does, but the number itself is the answer. */
function coverTone(remaining: number, available: number): string {
  if (remaining < 0) return "bg-red-500/85 text-white";
  if (available <= 0) return "bg-muted/30 text-muted-foreground";
  const left = remaining / available;
  if (left <= 0.15) return "bg-amber-500/80 text-white";
  if (left <= 0.4) return "bg-emerald-500/60 text-emerald-950 dark:text-emerald-50";
  return "bg-emerald-500/25";
}

/** Trim trailing zeros — a shop reads "18", not "18.00". */
const qty = (n: number) => Number(n.toFixed(2)).toLocaleString();

/** How many buckets this resource is at/over capacity in, out of how many it has
 *  numbers for.
 *
 *  The pinch-point callout finds the FIRST tight month, which answers "what do I move".
 *  This answers the other question, and it is the one a long horizon exists for: a
 *  resource over in 7 of 12 months is not a sequencing problem, it is a capacity
 *  problem, and that ratio is the argument for a shift, a hire, or a machine. One
 *  tight month buried among eleven slack ones is noise; seven is a decision.
 */
function overloadRatio(series: CapacityBucket[]): { over: number; measured: number } {
  const measured = series.filter((b) => b.utilization != null);
  return { over: measured.filter((b) => (b.utilization as number) >= 1).length,
           measured: measured.length };
}

function HeatRow({ name, series, critical }: {
  name: string; series: CapacityBucket[]; critical?: boolean;
}) {
  const { over, measured } = overloadRatio(series);
  return (
    <tr className="border-t">
      <th scope="row" className="sticky left-0 z-10 bg-background px-3 py-1.5 text-left text-xs font-medium">
        <span className="flex items-center gap-1.5">
          {/* Marked in the full view so a planner can see which rows the filter would
              keep without flipping it on and losing their place. */}
          {critical && (
            <Star aria-label="Critical resource"
                  className="h-3 w-3 shrink-0 fill-amber-400 text-amber-500" />
          )}
          <span className="truncate">{name}</span>
        </span>
      </th>
      <td className="px-2 py-1.5 text-center text-[11px] tabular-nums">
        {measured === 0 ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          <span
            className={over === 0 ? "text-muted-foreground"
              : over / measured >= 0.5 ? "font-semibold text-red-600 dark:text-red-400"
              : "text-amber-600 dark:text-amber-400"}
            title={`Over capacity in ${over} of ${measured} month(s) with data.
`
              + `Sustained overload is a capacity decision (shift / hire / machine); `
              + `a single month is a sequencing one.`}
          >
            {over}/{measured}
          </span>
        )}
      </td>
      {series.map((b) => (
        <td key={b.bucket} className="p-0.5">
          <div
            className={`rounded px-1.5 py-1.5 text-center text-[11px] tabular-nums ${tone(b.utilization)}`}
            title={`${name} · ${b.bucket}\n${b.load_hours}h load / ${b.capacity_hours}h capacity`}
          >
            {pct(b.utilization)}
          </div>
        </td>
      ))}
    </tr>
  );
}

/** Whole days from today to `iso`. Negative = already past. */
function daysFromToday(iso: string): number {
  const d = new Date(`${iso}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86_400_000);
}

const fmtDate = (iso: string | null) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined,
    { month: "short", day: "numeric", year: "numeric" }) : "—";

/** One line of the release list. Late-to-release is the state worth acting on, so it
 *  gets the colour; everything else stays quiet.
 *
 *  Release lives here rather than only in the Control Center because this is the one
 *  surface that knows WHEN an order has to start — which is what makes the readiness
 *  question urgent in the first place. The gate itself is advisory: a blocked order
 *  comes back 409 with its reasons, and a planner can still release with a recorded
 *  override, because the system knowing a job isn't ready doesn't mean it's wrong to
 *  start it. */
function ReleaseRow({ r }: { r: PlannedRelease }) {
  const days = daysFromToday(r.planned_start);
  const release = useReleaseForScheduling();
  const [blockers, setBlockers] = useState<ReleaseCheck[] | null>(null);
  const [reason, setReason] = useState("");

  const doRelease = (override?: string) =>
    release.mutate(
      { id: r.work_order_id, override_reason: override },
      {
        onSuccess: () => { setBlockers(null); setReason(""); },
        onError: (e: unknown) => {
          // 409 = not ready. The blockers are the useful part, so surface them inline
          // rather than a toast that says "failed" and drops the reasons.
          const found = (e as { response?: { data?: { blockers?: ReleaseCheck[] } } })
            ?.response?.data?.blockers;
          setBlockers(found ?? [{ code: "error", detail: "Release failed." }]);
        },
      }
    );

  return (
    <tr className="border-t">
      <td className="px-3 py-2">
        {/* The legacy detail path — it's the one that exists. Not adding a route in
            that style, just linking to it until the URL modernisation pass. */}
        <Link
          to="/workorder/$workOrderId"
          params={{ workOrderId: r.work_order_id }}
          className="font-mono text-xs hover:underline"
        >
          {r.erp_id}
        </Link>
      </td>
      <td className="px-3 py-2 text-xs tabular-nums">
        <span className={r.overdue ? "font-semibold text-red-600 dark:text-red-400" : ""}>
          {fmtDate(r.planned_start)}
        </span>
        {r.is_estimate && (
          <span
            className="ml-1.5 text-[10px] text-muted-foreground"
            title="Derived from the due date and lead time — no release date was set on this order."
          >
            est.
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-right text-xs tabular-nums text-muted-foreground">
        {days < 0 ? `${-days}d late` : days === 0 ? "today" : `in ${days}d`}
      </td>
      <td className="px-3 py-2 text-xs tabular-nums text-muted-foreground">
        {fmtDate(r.due_date)}
      </td>
      <td className="px-3 py-2 text-right">
        {r.released ? (
          <span className="text-xs text-muted-foreground">Released</span>
        ) : (
          <Button
            size="sm"
            variant={r.overdue ? "default" : "outline"}
            disabled={release.isPending}
            onClick={() => doRelease()}
          >
            {release.isPending ? "Releasing…" : "Release"}
          </Button>
        )}

        {blockers && (
          <div className="mt-2 space-y-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-2 text-left">
            <p className="text-xs font-medium">Not ready:</p>
            <ul className="space-y-0.5">
              {blockers.map((b) => (
                <li key={b.code} className="text-[11px] text-muted-foreground">
                  {b.detail}
                </li>
              ))}
            </ul>
            {/* Advisory, not blocking — a planner may know something the data doesn't.
                The reason is required so the override is a decision on the record. */}
            <Input
              className="h-7 text-xs"
              placeholder="Reason to release anyway…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!reason.trim() || release.isPending}
                onClick={() => doRelease(reason.trim())}
              >
                Release anyway
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setBlockers(null)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </td>
    </tr>
  );
}

export function CapacityPlanningPage() {
  const [months, setMonths] = useState(12);
  // Off by default: a planner who has never flagged anything would otherwise open an
  // empty heatmap and conclude the page is broken.
  const [criticalOnly, setCriticalOnly] = useState(false);
  const { data, isLoading } = useCapacityLoad(months, criticalOnly);

  const { data: partTypesData } = useRetrievePartTypes({ limit: 200 } as never);
  const partTypes = partTypesData?.results ?? [];

  const [partType, setPartType] = useState("");
  const [quantity, setQuantity] = useState("100");
  const [targetDate, setTargetDate] = useState("");
  const [submitted, setSubmitted] = useState<{
    part_type: string; quantity: number; target_date: string; months: number;
  } | null>(null);
  const quote = useCapableToPromise(submitted);

  // Memoised: `buckets` is a dependency of the pinch-point memo below.
  const buckets = useMemo(() => data?.buckets ?? [], [data]);

  // Where it gets tight first — the one line a planner actually acts on.
  const firstOverload = useMemo(() => {
    if (!data) return null;
    const rows = [
      { name: data.labor.name, series: data.labor.series },
      ...data.work_centers,
    ];
    let best: { name: string; bucket: string; u: number } | null = null;
    for (const r of rows) {
      for (const b of r.series) {
        if (b.utilization != null && b.utilization >= 0.85) {
          const idx = buckets.indexOf(b.bucket);
          if (!best || idx < buckets.indexOf(best.bucket)) {
            best = { name: r.name, bucket: b.bucket, u: b.utilization };
          }
          break;
        }
      }
    }
    return best;
  }, [data, buckets]);

  // Split rather than sorted: "already late to release" is a different decision from
  // "coming up", and burying the former in a date-ordered list hides the only rows that
  // need action today.
  const { overdue, upcoming } = useMemo(() => {
    const all = data?.planned_releases ?? [];
    return {
      overdue: all.filter((r) => r.overdue),
      upcoming: all.filter((r) => !r.overdue),
    };
  }, [data]);

  const exportCsv = () => {
    if (!data) return;
    const rows = [
      ["Labor", ...data.labor.series.map((b) => `${b.load_hours}/${b.capacity_hours}`)],
      ...data.work_centers.map((w) => [
        w.name, ...w.series.map((b) => `${b.load_hours}/${b.capacity_hours}`),
      ]),
    ];
    downloadCsv(`capacity_${new Date().toISOString().slice(0, 10)}`,
                ["Resource", ...buckets], rows);
  };

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Capacity planning</h1>
          <p className="text-sm text-muted-foreground">
            Rough-cut capacity vs committed load, month by month — the long view the
            30-day schedule can&rsquo;t give you.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={String(months)} onValueChange={(v) => setMonths(Number(v))}>
            <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              {HORIZONS.map((m) => (
                <SelectItem key={m} value={String(m)}>{m} months</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={!data}>
            Export CSV
          </Button>
        </div>
      </header>

      {/* Sits above the tabs because it qualifies everything on the page, not one view
          of it. An untimed operation costs zero hours and zero lead days, so it makes
          both the utilisation and the release dates read low with full confidence. */}
      {!!data?.untimed_orders?.length && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
          <strong>{data.untimed_orders.length}</strong>{" "}
          {data.untimed_orders.length === 1 ? "order has" : "orders have"} operations with
          no cycle time recorded, so their load and release dates below are understated.{" "}
          <span className="text-muted-foreground">
            {data.untimed_orders.slice(0, 4).map((o) => o.erp_id).join(", ")}
            {data.untimed_orders.length > 4 && `, +${data.untimed_orders.length - 4} more`}
            {" — set cycle and setup times on the step in the process editor."}
          </span>
        </div>
      )}

      <Tabs defaultValue="heatmap">
        <TabsList>
          <TabsTrigger value="heatmap">
            <Gauge className="mr-1.5 h-4 w-4" /> Capacity heatmap
          </TabsTrigger>
          <TabsTrigger value="releases">
            <Rocket className="mr-1.5 h-4 w-4" /> What to release
            {overdue.length > 0 && (
              <span className="ml-1.5 rounded bg-red-500/85 px-1.5 text-[10px] font-semibold text-white tabular-nums">
                {overdue.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="simulator">
            <CalendarClock className="mr-1.5 h-4 w-4" /> Could we take this order?
          </TabsTrigger>
        </TabsList>

        <TabsContent value="heatmap" className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            {firstOverload ? (
              <p className="min-w-0 flex-1 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
                First pinch point: <strong>{firstOverload.name}</strong> hits{" "}
                {pct(firstOverload.u)} in <strong>{firstOverload.bucket}</strong>.
              </p>
            ) : (
              <span className="min-w-0 flex-1" />
            )}
            {/* Rough-cut planning is defined over critical resources; a forty-centre
                shop has a handful anyone can act on. The filter changes what is shown
                and nothing else — load and capacity are computed over every centre
                either way, so a row's numbers are the same on both sides of it. */}
            <label className="flex shrink-0 cursor-pointer items-center gap-2 text-sm">
              <Switch checked={criticalOnly} onCheckedChange={setCriticalOnly} />
              <span className="whitespace-nowrap">Critical resources only</span>
              {data && (
                <span className="tabular-nums text-xs text-muted-foreground">
                  {data.work_centers.length}/{data.work_center_total}
                </span>
              )}
            </label>
          </div>

          <div className="overflow-x-auto rounded-lg border">
            {isLoading ? (
              <p className="p-4 text-sm text-muted-foreground">Computing capacity…</p>
            ) : !data ? (
              <p className="p-4 text-sm text-muted-foreground">No capacity data.</p>
            ) : (
              <table className="w-full border-separate border-spacing-0 text-sm">
                <thead>
                  <tr>
                    <th className="sticky left-0 z-10 bg-background px-3 py-2 text-left text-xs font-medium">
                      Resource
                    </th>
                    <th className="px-2 py-2 text-center text-[11px] font-medium text-muted-foreground"
                        title="Months at or over capacity, of those with data">
                      Over
                    </th>
                    {buckets.map((b) => (
                      <th key={b} className="px-1 py-2 text-center text-[11px] font-medium text-muted-foreground">
                        {b}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <HeatRow
                    name={`${data.labor.name} · ${data.labor.crew_size} crew`}
                    series={data.labor.series}
                  />
                  {data.work_centers.map((w) => (
                    <HeatRow key={w.id} name={w.name} series={w.series}
                             critical={w.is_critical} />
                  ))}

                  {/* Filtered down to nothing. The honest answer to "show me what I
                      said matters" when nothing is flagged — but it needs to say so,
                      and say where the flag lives, or the toggle reads as broken. */}
                  {criticalOnly && data.work_centers.length === 0 && (
                    <tr className="border-t">
                      <td colSpan={buckets.length + 2} className="px-3 py-6 text-center text-sm text-muted-foreground">
                        No work centre is flagged as critical.{" "}
                        <Link to="/admin/work-centers" className="underline underline-offset-2">
                          Flag the ones you watch
                        </Link>
                        , or turn this off to see all {data.work_center_total}.
                      </td>
                    </tr>
                  )}

                  {/* Materials share the grid but not the units — these cells are
                      cumulative demand against stock, not hours against capacity. Same
                      colour bands so a shortage reads at the same glance as an overload,
                      with the tooltip carrying the real quantities. */}
                  {data.materials?.length > 0 && (
                    <>
                      <tr className="border-t">
                        <th
                          scope="row"
                          colSpan={buckets.length + 2}   /* + Resource + Over */
                          className="sticky left-0 bg-background px-3 pb-1 pt-3 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                        >
                          Materials — stock left after committed work (negative = short)
                        </th>
                      </tr>
                      {data.materials.map((m) => (
                        <tr key={m.id} className="border-t">
                          <th scope="row" className="sticky left-0 z-10 bg-background px-3 py-1.5 text-left text-xs font-medium">
                            {m.name}
                          </th>
                          {/* A material has no "months over capacity" — it has a balance,
                              not a rate. Held empty so the buckets stay aligned with the
                              resource rows above rather than shifting a column left. */}
                          <td className="px-2 py-1.5 text-center text-[11px] text-muted-foreground">
                            {m.series.some((b) => b.short) ? "short" : "—"}
                          </td>
                          {m.series.map((b) => (
                            <td key={b.bucket} className="p-0.5">
                              <div
                                className={`rounded px-1.5 py-1.5 text-center text-[11px] tabular-nums ${coverTone(b.remaining_cover, b.available)}`}
                                title={`${m.name} · ${b.bucket}\n${qty(b.demand)} needed this month\n${qty(b.cumulative_demand)} committed to date · ${qty(b.available)} on hand and inbound\n${b.short ? `SHORT by ${qty(-b.remaining_cover)}` : `${qty(b.remaining_cover)} left`}`}
                              >
                                {qty(b.remaining_cover)}
                              </div>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  )}
                </tbody>
              </table>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-6 rounded bg-emerald-500/25" /> under 60%
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-6 rounded bg-emerald-500/60" /> 60–85%
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-6 rounded bg-amber-500/80" /> 85–100% (tight)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-6 rounded bg-red-500/85" /> over capacity
            </span>
            <span>
              · Load sits in the run-up to each order&rsquo;s due date &mdash; the months
              the work actually needs, not spread from today. Material cells show the
              quantity <em>left</em> after everything committed by that month &mdash; it
              falls as orders accrue and goes negative exactly when you&rsquo;re short.
            </span>
          </div>
        </TabsContent>

        <TabsContent value="releases" className="mt-4 space-y-4">
          <p className="text-sm text-muted-foreground">
            When each order has to <strong>start</strong> to hit its due date &mdash;
            due date less the time the work actually takes: run hours at each resource,
            vendor turnaround for outside processing, and the queue measured on your own
            floor. Suggestions only; nothing here changes an order&rsquo;s release date.
          </p>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Computing release dates&hellip;</p>
          ) : overdue.length === 0 && upcoming.length === 0 ? (
            <p className="rounded-lg border p-4 text-sm text-muted-foreground">
              Nothing to release in this horizon. Orders already in progress aren&rsquo;t
              listed &mdash; releasing them isn&rsquo;t a decision any more.
            </p>
          ) : (
            <div className="space-y-5">
              {overdue.length > 0 && (
                <div>
                  <h2 className="mb-1.5 text-sm font-semibold text-red-600 dark:text-red-400">
                    Late to release &mdash; {overdue.length}
                  </h2>
                  <p className="mb-2 text-xs text-muted-foreground">
                    The date these needed to start has passed and no work has begun, so
                    they are behind before they start. Release them, cut scope, or move
                    the promise.
                  </p>
                  <div className="overflow-x-auto rounded-lg border border-red-500/30">
                    <table className="w-full text-sm">
                      <thead className="bg-red-500/5 text-xs text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">Work order</th>
                          <th className="px-3 py-2 text-left font-medium">Should have started</th>
                          <th className="px-3 py-2 text-right font-medium">Slip</th>
                          <th className="px-3 py-2 text-left font-medium">Due</th>
                          <th className="px-3 py-2 text-right font-medium">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overdue.map((r) => (
                          <ReleaseRow key={r.work_order_id} r={r} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {upcoming.length > 0 && (
                <div>
                  <h2 className="mb-2 text-sm font-semibold">
                    Coming up &mdash; {upcoming.length}
                  </h2>
                  <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/40 text-xs text-muted-foreground">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">Work order</th>
                          <th className="px-3 py-2 text-left font-medium">Release by</th>
                          <th className="px-3 py-2 text-right font-medium">When</th>
                          <th className="px-3 py-2 text-left font-medium">Due</th>
                          <th className="px-3 py-2 text-right font-medium">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {upcoming.map((r) => (
                          <ReleaseRow key={r.work_order_id} r={r} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <p className="text-[11px] text-muted-foreground">
                <strong>est.</strong> means the date was derived rather than set on the
                order. Setting an earliest start on a work order overrides the estimate,
                and the queue figures sharpen as the floor records more history.
              </p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="simulator" className="mt-4 space-y-4">
          <div className="grid gap-3 rounded-lg border p-4 sm:grid-cols-4">
            <div className="grid gap-1 sm:col-span-2">
              <Label className="text-xs">Part type</Label>
              <Select value={partType} onValueChange={setPartType}>
                <SelectTrigger><SelectValue placeholder="Choose a part type" /></SelectTrigger>
                <SelectContent>
                  {partTypes.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Quantity</Label>
              <Input type="number" min="1" value={quantity}
                     onChange={(e) => setQuantity(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">Wanted by</Label>
              <Input type="date" value={targetDate}
                     onChange={(e) => setTargetDate(e.target.value)} />
            </div>
            <div className="sm:col-span-4">
              <Button
                disabled={!partType || Number(quantity) <= 0 || !targetDate}
                onClick={() => setSubmitted({
                  part_type: partType, quantity: Number(quantity),
                  target_date: targetDate, months,
                })}
              >
                Check capacity
              </Button>
            </div>
          </div>

          {quote.isFetching && (
            <p className="text-sm text-muted-foreground">Checking…</p>
          )}

          {quote.data && !quote.isFetching && (
            <div className="space-y-3 rounded-lg border p-4">
              <p className="text-lg font-semibold">
                {quote.data.feasible ? (
                  <span className="text-emerald-600 dark:text-emerald-400">
                    Yes — capacity exists by {quote.data.target_bucket}.
                  </span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">
                    Not by {quote.data.target_bucket ?? "then"}.
                  </span>
                )}
              </p>

              {quote.data.reason && (
                <p className="text-sm text-muted-foreground">{quote.data.reason}</p>
              )}

              {/* "No" without a reason is useless to whoever has to answer the
                  customer — always name what runs out, and when it would work. */}
              {!quote.data.feasible && !!quote.data.binding_resources?.length && (
                <div className="space-y-1 text-sm">
                  <p className="font-medium">What runs out:</p>
                  <ul className="space-y-0.5">
                    {/* Backend sorts worst-first; show the few that matter. An order
                        that badly overruns the shop trips every resource, and the full
                        list buries the actual constraint. */}
                    {quote.data.binding_resources.slice(0, 3).map((b) => (
                      <li key={b.resource} className="text-muted-foreground">
                        <strong className="text-foreground">{b.resource}</strong> — needs{" "}
                        {b.need}h, only {b.free_through_target}h free by then.
                      </li>
                    ))}
                    {quote.data.binding_resources.length > 3 && (
                      <li className="text-muted-foreground">
                        + {quote.data.binding_resources.length - 3} other resource(s) short.
                      </li>
                    )}
                  </ul>
                  <p className="pt-1">
                    {quote.data.earliest_feasible_bucket
                      ? <>Earliest it fits: <strong>{quote.data.earliest_feasible_bucket}</strong>.</>
                      : <>It doesn&rsquo;t fit anywhere in this horizon — it needs overtime, an
                         extra shift, or subcontract.</>}
                  </p>
                </div>
              )}

              {quote.data.work_content_hours && (
                <div className="text-xs text-muted-foreground">
                  Work content:{" "}
                  {Object.entries(quote.data.work_content_hours)
                    .map(([k, v]) => `${k} ${v}h`)
                    .join(" · ")}
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
