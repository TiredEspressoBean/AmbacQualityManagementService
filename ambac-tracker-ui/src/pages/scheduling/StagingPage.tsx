/** Staging pick list (/production/staging).
 *
 * A materials handler's worksheet, not a report. They read it walking the floor with
 * a cart, so it's ordered the way the work arrives and says what to pick, in what
 * quantity, for which bench — and flags what isn't there so they escalate before the
 * operator discovers it.
 *
 * Everything here comes off the SCHEDULE, so it only says anything once a solve has
 * run. That's also the point: the scheduler makes time-specific promises, and this is
 * what makes them true.
 */
import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, PackageCheck, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ReportButton } from "@/components/reports/ReportButton";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { useStagingList, useMarkStaged, type StagingJob } from "@/hooks/useScheduling";

const WINDOWS = [4, 8, 12, 24];
const ALL = "__all__";

/** "in 20m" / "in 3h" / "09:40" — a handler cares how soon, not the timestamp. */
function whenLabel(iso: string): string {
  const t = new Date(iso).getTime();
  const mins = Math.round((t - Date.now()) / 60000);
  if (mins <= 0) return "now";
  if (mins < 60) return `in ${mins}m`;
  if (mins < 8 * 60) return `in ${Math.round(mins / 60)}h`;
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit", minute: "2-digit",
  });
}

function JobCard({ job, onToggle, busy }: {
  job: StagingJob;
  onToggle: (job: StagingJob, staged: boolean) => void;
  busy: boolean;
}) {
  const short = job.short_count > 0;
  const staged = !!job.staged_at;
  return (
    <div
      className={`rounded-lg border p-3 ${
        short ? "border-l-4 border-l-amber-500" : ""
      } ${staged ? "bg-muted/30" : ""}`}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <Checkbox
          className="mr-0.5 translate-y-0.5"
          checked={staged}
          disabled={busy}
          aria-label={staged ? "Mark not staged" : "Mark staged"}
          onCheckedChange={(v) => onToggle(job, v === true)}
        />
        <span className={`font-mono text-sm font-medium ${staged ? "line-through opacity-60" : ""}`}>
          {job.erp_id}
        </span>
        <span className="text-xs text-muted-foreground">{job.step_name}</span>
        {job.part_type && (
          <span className="truncate text-xs text-muted-foreground">
            · {job.part_type}
          </span>
        )}
        <span className="ml-auto shrink-0 text-xs tabular-nums">
          <strong>{job.units}</strong> unit{job.units === 1 ? "" : "s"}
          {" · "}
          <span className={short ? "text-amber-700 dark:text-amber-400" : ""}>
            {whenLabel(job.starts_at)}
          </span>
        </span>
      </div>

      {job.materials.length > 0 ? (
        <table className="mt-2 w-full text-xs">
          <tbody>
            {job.materials.map((m) => (
              <tr key={m.material} className="border-t first:border-t-0">
                <td className="py-1 pr-2">
                  {m.material}
                  {m.optional && (
                    <span className="ml-1 text-muted-foreground">(optional)</span>
                  )}
                </td>
                <td className="w-20 py-1 text-right tabular-nums">
                  <strong>{m.needed}</strong>
                </td>
                <td className="w-56 py-1 pl-2 text-right">
                  {m.short > 0 ? (
                    <span className="tabular-nums text-amber-700 dark:text-amber-400">
                      short {m.short}
                    </span>
                  ) : m.lots.length > 0 ? (
                    // Naming the lot matters: consumption records oldest-expiry, so a
                    // picker grabbing a different one desynchronises the traceability
                    // record from what physically went in.
                    <span className="text-muted-foreground">
                      {m.lots.map((l) => l.lot_number).join(", ")}
                      {m.lots[0].storage_location && (
                        <span className="ml-1">· {m.lots[0].storage_location}</span>
                      )}
                    </span>
                  ) : (
                    <span className="tabular-nums text-muted-foreground">
                      {m.on_hand} on hand
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mt-1.5 text-xs text-muted-foreground">
          No material consumed at this step.
        </p>
      )}

      {job.fixtures.length > 0 && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Wrench className="h-3 w-3" /> {job.fixtures.join(" · ")}
        </p>
      )}

      {/* Who has it — the shift-handover question. */}
      {staged && job.staged_by && (
        <p className="mt-1.5 text-xs text-muted-foreground">
          Staged by {job.staged_by}
        </p>
      )}
    </div>
  );
}

export function StagingPage() {
  // Two lenses on the same data. "Deliver" groups by station — right for dropping
  // material off. "Pick" groups by material — right for the walk TO the crib, where
  // visiting the seal bin once for six jobs beats six trips.
  const [lens, setLens] = useState<"deliver" | "pick">("deliver");
  const [station, setStation] = useState<string>(ALL);
  const [hours, setHours] = useState(8);
  const { data, isLoading, isError, refetch, isFetching } = useStagingList(
    station === ALL ? undefined : station, hours);

  // Station picker options. Queried directly rather than through a hook, matching
  // how the work-centre admin page reads the same list.
  const markStaged = useMarkStaged();
  const toggleStaged = (job: StagingJob, staged: boolean) =>
    markStaged.mutate({ work_order: job.work_order_id, step: job.step_id, staged });

  const { data: wcData } = useQuery({
    queryKey: ["work-centers", "staging-picker"] as const,
    queryFn: () => api.api_WorkCenters_list({ queries: { limit: 100 } } as never),
  });
  const workCenters: { id: string; name: string }[] = wcData?.results ?? [];

  // One row per material across every station, with where each portion goes.
  // Every material across every station, with each portion's destination AND
  // whether it's already at the bench. Staged rows STAY on the list, ticked —
  // a pick sheet you can't see your own progress on is worse than paper.
  const pickRows = useMemo(() => {
    const by = new Map<string, {
      material: string; total: number; remaining: number; short: number;
      location: string; lots: string[];
      drops: { qty: number; station: string; erp: string; staged: boolean }[];
    }>();
    for (const st of data?.stations ?? []) {
      for (const j of st.jobs) {
        const staged = !!j.staged_at;
        for (const m of j.materials) {
          const row = by.get(m.material) ?? {
            material: m.material, total: 0, remaining: 0, short: 0,
            location: m.lots[0]?.storage_location ?? "", lots: [], drops: [],
          };
          row.total += m.needed;
          if (!staged) {
            row.remaining += m.needed;
            row.short += m.short;
            for (const l of m.lots) {
              if (!row.lots.includes(l.lot_number)) row.lots.push(l.lot_number);
            }
          }
          row.drops.push({ qty: m.needed, station: st.name, erp: j.erp_id, staged });
          by.set(m.material, row);
        }
      }
    }
    return [...by.values()].sort(
      (a, b) => (b.short - a.short)
        || (b.remaining > 0 ? 1 : 0) - (a.remaining > 0 ? 1 : 0)
        || a.material.localeCompare(b.material));
  }, [data]);

  // How many scheduled jobs contribute nothing to this lens. Without this the
  // by-station and by-material tabs look wildly inconsistent for no stated
  // reason — 15 jobs on one, two lines on the other.
  const noMaterialJobs = useMemo(
    () => (data?.stations ?? []).reduce(
      (n, s) => n + s.jobs.filter((j) => j.materials.length === 0).length, 0),
    [data]);

  const totalJobs = (data?.stations ?? []).reduce((n, s) => n + s.jobs.length, 0);
  const totalShort = (data?.stations ?? []).reduce((n, s) => n + s.short_count, 0);

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Staging list</h1>
          <p className="text-sm text-muted-foreground">
            What to put at each bench before the operator gets there — the next{" "}
            {data?.window_hours ?? hours} hours of scheduled work.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-md border p-0.5">
            {([["deliver", "By station"], ["pick", "By material"]] as const).map(
              ([v, label]) => (
                <Button
                  key={v}
                  variant={lens === v ? "secondary" : "ghost"}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => setLens(v)}
                >
                  {label}
                </Button>
              ))}
          </div>
          <Select value={station} onValueChange={setStation}>
            <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All stations</SelectItem>
              {workCenters.map((w) => (
                <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={String(hours)} onValueChange={(v) => setHours(Number(v))}>
            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
            <SelectContent>
              {WINDOWS.map((h) => (
                <SelectItem key={h} value={String(h)}>next {h}h</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <ReportButton
            reportType="staging_list"
            label="PDF"
            params={{ hours, ...(station === ALL ? {} : { work_center: station }) }}
          />
          <Button variant="outline" size="sm" onClick={() => refetch()}
                  disabled={isFetching}>
            {isFetching ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
      </header>

      {/* A stale plan means these times have already moved — say so before someone
          stages to them. */}
      {data?.is_stale && (
        <p className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
          The schedule is stale — these times may have moved. Re-solve before staging
          to them.
        </p>
      )}

      {totalShort > 0 && (
        <p className="flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
          <span>
            <strong>{totalShort}</strong> line{totalShort === 1 ? "" : "s"} can&rsquo;t
            be picked in full. Escalate now rather than at the bench.
          </span>
        </p>
      )}

      {/* Can't be staged anywhere, so it would otherwise read as "nothing to pick"
          — surface it as a BOM to fix instead. */}
      {(data?.unmapped?.length ?? 0) > 0 && (
        <div className="rounded-md border border-sky-500/40 bg-sky-500/5 px-3 py-2 text-sm">
          <p className="font-medium">Some components aren&rsquo;t mapped to a step</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            These are needed but the BOM doesn&rsquo;t say at which operation, so they
            can&rsquo;t be put on a bench list. Set <em>consumed at step</em> on the BOM
            line to have them picked here.
          </p>
          <ul className="mt-1.5 space-y-0.5 text-xs">
            {data!.unmapped.map((u) => (
              <li key={u.erp_id}>
                <span className="font-mono">{u.erp_id}</span>{" — "}
                <span className="text-muted-foreground">{u.components.join(", ")}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {isError && (
        <div className="space-y-2 text-sm">
          <p className="text-destructive">Couldn&rsquo;t load the staging list.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Try again</Button>
        </div>
      )}

      {/* "Nothing to stage" and "there is no plan" are different facts. */}
      {data?.note && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-12 text-center">
          <PackageCheck className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">{data.note}</p>
        </div>
      )}

      {data && !data.note && totalJobs === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-12 text-center">
          <CheckCircle2 className="h-8 w-8 text-emerald-600" />
          <p className="text-sm font-medium">Nothing scheduled in this window.</p>
          <p className="text-xs text-muted-foreground">
            Try a longer window, or check the schedule board.
          </p>
        </div>
      )}

      {/* Jobs exist but none carry material. Staged rows STAY in pickRows, so an
          empty list can only mean this — not "it's all been picked". Without the
          state the page renders blank: the station grid is hidden and the
          "nothing scheduled" state doesn't apply. */}
      {lens === "pick" && pickRows.length === 0 && totalJobs > 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-12 text-center">
          <PackageCheck className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">Nothing to pick in this window.</p>
          <p className="max-w-md text-xs text-muted-foreground">
            All {totalJobs} scheduled job{totalJobs === 1 ? "" : "s"} consume no
            material at their step, so there is nothing to fetch from stores. Switch
            to <strong>By station</strong> to see the work itself.
          </p>
        </div>
      )}

      {lens === "pick" && pickRows.length > 0 && (
        <div className="space-y-2">
          {noMaterialJobs > 0 && (
            <p className="text-xs text-muted-foreground">
              {noMaterialJobs} of {totalJobs} scheduled job
              {totalJobs === 1 ? "" : "s"} consume no material at their step, so
              they don&rsquo;t appear here — see <strong>By station</strong> for the
              work itself.
            </p>
          )}
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Pick</th>
                  <th className="w-24 px-3 py-2 text-right font-medium">Qty</th>
                  <th className="px-3 py-2 text-left font-medium">Lot · location</th>
                  <th className="px-3 py-2 text-left font-medium">Deliver to</th>
                </tr>
              </thead>
              <tbody>
                {pickRows.map((r) => {
                  const done = r.remaining === 0;
                  return (
                    <tr key={r.material}
                        className={`border-t align-top ${done ? "bg-muted/30" : ""}`}>
                      <td className="px-3 py-2">
                        <span className={done ? "text-muted-foreground line-through" : ""}>
                          {r.material}
                        </span>
                        {r.short > 0 && (
                          <span className="ml-2 text-xs text-amber-700 dark:text-amber-400">
                            short {r.short}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right font-medium tabular-nums">
                        {done ? (
                          <span className="text-xs font-normal text-muted-foreground">
                            all staged
                          </span>
                        ) : r.remaining === r.total ? (
                          r.total
                        ) : (
                          // Remaining vs total, so the handler sees both what's
                          // left to fetch and what the job actually needs.
                          <>
                            {r.remaining}
                            <span className="text-xs font-normal text-muted-foreground">
                              {" "}of {r.total}
                            </span>
                          </>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {done ? "—" : (r.lots.join(", ") || "—")}
                        {!done && r.location && <div>{r.location}</div>}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {r.drops.map((d, i) => (
                          <div key={i} className={d.staged ? "text-muted-foreground/60" : ""}>
                            <span className="inline-block w-3">{d.staged ? "✓" : ""}</span>
                            <span className={`tabular-nums ${d.staged ? "line-through" : ""}`}>
                              {d.qty}
                            </span>{" "}
                            → {d.station}{" "}
                            <span className="font-mono">{d.erp}</span>
                          </div>
                        ))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className={`grid gap-5 lg:grid-cols-2 ${lens === "pick" ? "hidden" : ""}`}>
        {(data?.stations ?? []).map((s) => (
          <section key={s.work_center_id} className="space-y-2">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              {s.name}
              <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                {s.jobs.length} job{s.jobs.length === 1 ? "" : "s"}
              </Badge>
              <span className="text-xs font-normal text-muted-foreground">
                {s.staged_count}/{s.jobs.length} staged
              </span>
              {s.short_count > 0 && (
                <Badge
                  variant="outline"
                  className="h-5 border-amber-500/50 px-1.5 text-[10px] text-amber-700 dark:text-amber-400"
                >
                  {s.short_count} short
                </Badge>
              )}
            </h2>
            <div className="space-y-2">
              {s.jobs.map((j) => (
                <JobCard
                  key={`${j.work_order_id}-${j.step_id}`}
                  job={j}
                  onToggle={toggleStaged}
                  busy={markStaged.isPending}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
