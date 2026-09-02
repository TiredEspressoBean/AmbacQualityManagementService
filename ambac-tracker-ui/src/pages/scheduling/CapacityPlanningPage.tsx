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
import { CalendarClock, Gauge } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useCapacityLoad, useCapableToPromise, type CapacityBucket,
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

function HeatRow({ name, series }: { name: string; series: CapacityBucket[] }) {
  return (
    <tr className="border-t">
      <th scope="row" className="sticky left-0 z-10 bg-background px-3 py-1.5 text-left text-xs font-medium">
        {name}
      </th>
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

export function CapacityPlanningPage() {
  const [months, setMonths] = useState(12);
  const { data, isLoading } = useCapacityLoad(months);

  const { data: partTypesData } = useRetrievePartTypes({ limit: 200 } as never);
  const partTypes = (partTypesData as any)?.results ?? [];

  const [partType, setPartType] = useState("");
  const [quantity, setQuantity] = useState("100");
  const [targetDate, setTargetDate] = useState("");
  const [submitted, setSubmitted] = useState<{
    part_type: string; quantity: number; target_date: string; months: number;
  } | null>(null);
  const quote = useCapableToPromise(submitted);

  const buckets = data?.buckets ?? [];

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

      <Tabs defaultValue="heatmap">
        <TabsList>
          <TabsTrigger value="heatmap">
            <Gauge className="mr-1.5 h-4 w-4" /> Capacity heatmap
          </TabsTrigger>
          <TabsTrigger value="simulator">
            <CalendarClock className="mr-1.5 h-4 w-4" /> Could we take this order?
          </TabsTrigger>
        </TabsList>

        <TabsContent value="heatmap" className="mt-4 space-y-3">
          {firstOverload && (
            <p className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
              First pinch point: <strong>{firstOverload.name}</strong> hits{" "}
              {pct(firstOverload.u)} in <strong>{firstOverload.bucket}</strong>.
            </p>
          )}

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
                    <HeatRow key={w.id} name={w.name} series={w.series} />
                  ))}
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
            <span>· Load is spread across each order&rsquo;s start→due window.</span>
          </div>
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
