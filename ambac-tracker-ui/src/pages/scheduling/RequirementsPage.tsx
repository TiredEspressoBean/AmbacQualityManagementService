/** Sourcing & production requirements report (/production/requirements).
 *
 * What open demand needs, so purchasing/receiving and production know what to act on
 * and by when. Three lanes (source / produce / tooling) with lead-time-driven order-by
 * dates; rows past their order-by are flagged. Export to spreadsheet (CSV) or PDF.
 */
import { Link } from "@tanstack/react-router";
import { ClipboardList, Download, Truck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReportButton } from "@/components/reports/ReportButton";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { ExpectFromShortagesDialog } from "@/components/receiving/ExpectFromShortagesDialog";
import { usePlanTeardown } from "@/hooks/usePlanTeardown";
import { useRequirements, type RecoverRow } from "@/hooks/useScheduling";
import { useState } from "react";
import { toast } from "sonner";
import { downloadCsv } from "@/lib/csv";
import { cn } from "@/lib/utils";

const fmt = (d: string | null) =>
  d ? new Date(d + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";

const todayISO = new Date().toISOString().slice(0, 10);

/** Accept a teardown proposal: plan a teardown work order for the proposed cores,
 *  dated to the start-by (editable). Nothing starts until an operator begins it. */
function PlanTeardownButton({ row }: { row: RecoverRow }) {
  const [open, setOpen] = useState(false);
  const [startBy, setStartBy] = useState(row.start_by ?? "");
  const plan = usePlanTeardown();
  const n = row.candidate_cores.length;
  const lotUnits = row.candidate_lots.reduce((sum, l) => sum + l.quantity, 0);
  const noun = `${row.core_type} core${n === 1 ? "" : "s"}`;

  const submit = () =>
    plan.mutate(
      { core_ids: row.candidate_cores.map((c) => c.id), start_by: startBy || null },
      {
        onSuccess: (res) => {
          toast.success(`Planned ${res.work_order_erp_id}: ${n} ${noun}`);
          setOpen(false);
        },
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail;
          toast.error(detail ?? "Could not plan the teardown.");
        },
      },
    );

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setStartBy(row.start_by ?? "");
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" disabled={n === 0}>
          Plan teardown
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Plan teardown of {n} {noun}</DialogTitle>
          <DialogDescription>
            Creates a planned teardown work order and commits these cores to it.
            Disassembly starts when an operator begins the first step, not now.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <div>
            <div className="mb-1 text-muted-foreground">Cores, oldest received first</div>
            <div className="font-mono text-xs">
              {row.candidate_cores.map((c) => c.core_number).join(", ")}
            </div>
          </div>
          {lotUnits > 0 && (
            <p className="rounded border border-amber-300/60 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-200">
              The proposal also draws {lotUnits} unit{lotUnits === 1 ? "" : "s"} from{" "}
              {row.candidate_lots.map((l) => `${l.lot_number} (${l.quantity})`).join(", ")}.
              Those have no identity yet, so this plans only the {n} identified.{" "}
              <Link to="/reman/core-lots" className="underline">Identify them on Core lots</Link>
              {" "}and the next proposal commits them.
            </p>
          )}
          <label className="block">
            <span className="mb-1 block text-muted-foreground">Start by</span>
            <Input type="date" value={startBy} onChange={(e) => setStartBy(e.target.value)} />
            {!row.start_by && (
              <span className="mt-1 block text-xs text-muted-foreground">
                No teardown duration is authored for this core type, so there is no
                suggested date. Leave it blank to let the scheduler place it.
              </span>
            )}
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={plan.isPending}>
            {plan.isPending ? "Planning…" : "Plan teardown"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
const isLate = (orderBy: string | null) => !!orderBy && orderBy < todayISO;

function Section({
  title, subtitle, children, empty, count, action,
}: {
  title: string; subtitle: string; children: React.ReactNode; empty: boolean; count: number;
  action?: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <div className="flex items-center gap-3">
          {action}
          <span className="text-xs text-muted-foreground">{count} item{count === 1 ? "" : "s"}</span>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{subtitle}</p>
      <div className="overflow-x-auto rounded-lg border">
        {empty ? (
          <p className="p-4 text-sm text-muted-foreground">Nothing outstanding.</p>
        ) : (
          <table className="w-full text-sm">{children}</table>
        )}
      </div>
    </section>
  );
}

export function RequirementsPage() {
  const { data, isLoading } = useRequirements();
  const source = data?.source ?? [];
  const produce = data?.produce ?? [];
  const tooling = data?.tooling ?? [];
  const recover = data?.recover ?? [];
  // Shortage rows ticked to raise expected receipts from. Keyed by item, not index,
  // so a refetch that reorders the lane keeps the right rows ticked.
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [expectOpen, setExpectOpen] = useState(false);
  const keyOf = (r: (typeof source)[number]) => `${r.buy_kind}:${r.item_id}`;
  const pickedRows = source.filter((r) => picked.has(keyOf(r)));
  const toggle = (k: string, on: boolean) =>
    setPicked((p) => { const n = new Set(p); if (on) n.add(k); else n.delete(k); return n; });

  const exportCsv = () =>
    downloadCsv(
      `requirements_${todayISO}`,
      ["Lane", "Item", "Kind / Component", "Qty", "Need by", "Order by", "Notes"],
      [
        ...source.map((r) => ["Source", r.material, "Buy", r.qty_short, r.need_by ?? "", r.order_by ?? "",
          [r.incoming_date ? `incoming ${r.incoming_date}` : "",
           (r.recoverable ?? 0) > 0
             ? `recoverable ${r.recoverable} from ${r.recoverable_cores} cores`
             : ""].filter(Boolean).join("; ")]),
        ...recover.map((r) => ["Recover", r.core_type, `tear down ${r.cores_to_tear_down}`,
          r.cores_to_tear_down, r.need_by ?? "", r.start_by ?? "",
          r.components.map((c) => `${c.component} ${c.covered_by_teardown}/${c.needed}`).join("; ")]),
        ...produce.map((r) => ["Produce", r.component, r.work_order, r.qty, r.need_by ?? "", "", r.status]),
        ...tooling.map((r) => ["Tooling", r.fixture, r.kind, "", "", r.order_by ?? "", ""]),
      ]
    );

  // Recover counts: a sheet whose only content is a teardown proposal is still worth
  // exporting.
  const anyRows = source.length + recover.length + produce.length + tooling.length > 0;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-6">
        <div className="h-8 w-64 animate-pulse rounded bg-muted" />
        <div className="h-40 animate-pulse rounded bg-muted" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary">
            <ClipboardList className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Sourcing &amp; production requirements</h1>
            <p className="text-sm text-muted-foreground">
              What open demand needs — material to buy, components to build, tooling to procure —
              with order-by dates from the live schedule. Rows past their order-by are flagged.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={!anyRows}>
            <Download className="mr-1.5 h-4 w-4" /> CSV
          </Button>
          <ReportButton reportType="requirements" label="PDF" allowEmail params={{}} />
        </div>
      </div>

      <Section
        title="Source (buy)"
        subtitle="Purchased materials short of coverage across open work orders."
        empty={source.length === 0}
        count={source.length}
        action={
          <Button size="sm" variant="outline" disabled={pickedRows.length === 0}
            onClick={() => setExpectOpen(true)}>
            <Truck className="mr-1.5 h-4 w-4" />
            Expect{pickedRows.length > 0 ? ` ${pickedRows.length}` : ""}
          </Button>
        }
      >
        <thead>
          <tr className="border-b bg-muted/40 text-left text-muted-foreground">
            <th className="w-10 p-3">
              <Checkbox
                aria-label="Select all shortages"
                checked={source.length > 0 && pickedRows.length === source.length}
                onCheckedChange={(on) => setPicked(on ? new Set(source.map(keyOf)) : new Set())}
              />
            </th>
            <th className="p-3 font-medium">Material</th>
            <th className="p-3 text-right font-medium">Short</th>
            <th
              className="p-3 text-right font-medium"
              title="What the core bank could yield. A forecast — teardown hasn't happened — so it is shown beside the shortfall, never subtracted from it."
            >
              Recoverable
            </th>
            <th className="p-3 font-medium">Lead time</th>
            <th className="p-3 font-medium">Need by</th>
            <th className="p-3 font-medium">Order by</th>
            <th className="p-3 font-medium">Incoming</th>
          </tr>
        </thead>
        <tbody>
          {source.map((r) => (
            <tr key={keyOf(r)} className="border-b last:border-0 hover:bg-muted/30">
              <td className="p-3">
                <Checkbox
                  aria-label={`Select ${r.material}`}
                  checked={picked.has(keyOf(r))}
                  onCheckedChange={(on) => toggle(keyOf(r), on === true)}
                />
              </td>
              <td className="p-3">
                <div className="font-medium">{r.material}</div>
                {(r.part_number || r.preferred_supplier_name) && (
                  <div className="text-xs text-muted-foreground">
                    {[r.part_number, r.preferred_supplier_name].filter(Boolean).join(" · ")}
                  </div>
                )}
              </td>
              <td className="p-3 text-right tabular-nums">
                {r.qty_short}
                {/* Beside the short figure, never inside it: purchasing may buy ahead
                    on a forecast, and nothing here makes them. */}
                {(r.forecast_short ?? 0) > 0 && (
                  <div
                    className="text-xs text-muted-foreground"
                    title="Expected replacements on repair-and-return units not yet torn down."
                  >
                    +{r.forecast_short} forecast
                  </div>
                )}
              </td>
              <td className="p-3 text-right tabular-nums">
                {(r.recoverable ?? 0) > 0 ? (
                  <span
                    className="text-emerald-700 dark:text-emerald-400"
                    title={(r.recoverable_sources ?? [])
                      .map((s) => `${s.cores} × ${s.core_type} @ ${s.per_core} each`)
                      .join(" · ")}
                  >
                    {r.recoverable}
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({r.recoverable_cores} cores)
                    </span>
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
              <td className="p-3">{r.lead_time_days == null ? "—" : `${r.lead_time_days}d`}</td>
              <td className="p-3">{fmt(r.need_by)}</td>
              <td className={cn("p-3", isLate(r.order_by) && "font-medium text-destructive")}>
                {fmt(r.order_by)}
                {isLate(r.order_by) && <Badge variant="destructive" className="ml-2">order now</Badge>}
              </td>
              <td className="p-3 text-muted-foreground">
                {r.incoming_date ? `due ${fmt(r.incoming_date)}` : "none"}
              </td>
            </tr>
          ))}
        </tbody>
      </Section>
      <ExpectFromShortagesDialog
        rows={pickedRows}
        open={expectOpen}
        onOpenChange={setExpectOpen}
        onDone={() => setPicked(new Set())}
      />

      {/* Between Source and Produce because that is the order the decision is made in.
          One row per CORE TYPE — one core yields several components, so a per-component
          list would ask for the same unit repeatedly. It covers replacement slots on
          exchange rebuilds, after what is on the shelf and what committed teardowns
          will yield; accepting a row plans the teardown and it drops off this list. */}
      <Section
        title="Recover (tear down)"
        subtitle="Teardown proposed to refill recovered stock for exchange rebuilds. Planning one commits those cores; nothing here commits a core on its own."
        empty={recover.length === 0}
        count={recover.length}
      >
        <thead>
          <tr className="border-b bg-muted/40 text-left text-muted-foreground">
            <th className="p-3 font-medium">Core type</th>
            <th className="p-3 text-right font-medium">Tear down</th>
            <th className="p-3 font-medium">Covers</th>
            <th className="p-3 font-medium">Start by</th>
            <th className="p-3" />
          </tr>
        </thead>
        <tbody>
          {recover.map((r) => (
            <tr key={r.core_type_id} className="border-b align-top last:border-0 hover:bg-muted/30">
              <td className="p-3">
                <div className="font-medium">{r.core_type}</div>
                <div className="text-xs text-muted-foreground">
                  {r.cores_available} in bank
                  {r.cores_in_flight > 0 && ` · ${r.cores_in_flight} already committed`}
                  {r.candidate_lots.length > 0 && (
                    <> · {r.candidate_lots.reduce((s, l) => s + l.quantity, 0)} of the proposal
                      from <Link to="/reman/core-lots" className="underline">bulk lots</Link></>
                  )}
                </div>
              </td>
              <td className="p-3 text-right tabular-nums">{r.cores_to_tear_down}</td>
              <td className="p-3">
                {r.components.map((c) => (
                  <div key={c.component}>
                    {c.component}{" "}
                    <span className="tabular-nums text-emerald-700 dark:text-emerald-400">
                      {c.covered_by_teardown}
                    </span>
                    <span className="ml-1 text-xs text-muted-foreground">
                      of {c.needed} needed
                      {c.on_shelf > 0 && ` · ${c.on_shelf} on shelf`}
                      {c.in_flight > 0 && ` · ${c.in_flight} on the way`}
                      {c.still_short > 0 && ` · ${c.still_short} still short`}
                    </span>
                  </div>
                ))}
              </td>
              <td className={cn("p-3", isLate(r.start_by) && "font-medium text-destructive")}>
                {r.start_by ? (
                  <>
                    {fmt(r.start_by)}
                    {isLate(r.start_by) && (
                      <Badge variant="destructive" className="ml-2">start now</Badge>
                    )}
                  </>
                ) : (
                  // No authored teardown duration: "—" is the honest answer, since a
                  // made-up date would be scheduled against as fact.
                  <span className="text-muted-foreground" title="No teardown duration authored for this core type.">
                    —
                  </span>
                )}
              </td>
              <td className="p-3 text-right">
                <PlanTeardownButton row={r} />
              </td>
            </tr>
          ))}
        </tbody>
      </Section>

      <Section
        title="Produce (build)"
        subtitle="In-house component work orders pegged to open demand."
        empty={produce.length === 0}
        count={produce.length}
      >
        <thead>
          <tr className="border-b bg-muted/40 text-left text-muted-foreground">
            <th className="p-3 font-medium">Work order</th>
            <th className="p-3 font-medium">Component</th>
            <th className="p-3 text-right font-medium">Qty</th>
            <th className="p-3 font-medium">Need by</th>
            <th className="p-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {produce.map((r, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
              <td className="p-3 font-mono text-xs">{r.work_order}</td>
              <td className="p-3">{r.component}</td>
              <td className="p-3 text-right tabular-nums">{r.qty}</td>
              <td className="p-3">{fmt(r.need_by)}</td>
              <td className="p-3"><Badge variant="secondary">{r.status}</Badge></td>
            </tr>
          ))}
        </tbody>
      </Section>

      <Section
        title="Tooling"
        subtitle="Fixtures, tools, dies, and NC programs not yet on hand."
        empty={tooling.length === 0}
        count={tooling.length}
      >
        <thead>
          <tr className="border-b bg-muted/40 text-left text-muted-foreground">
            <th className="p-3 font-medium">Resource</th>
            <th className="p-3 font-medium">Kind</th>
            <th className="p-3 font-medium">Lead time</th>
            <th className="p-3 font-medium">Order by</th>
          </tr>
        </thead>
        <tbody>
          {tooling.map((r, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
              <td className="p-3 font-medium">{r.fixture}</td>
              <td className="p-3">{r.kind}</td>
              <td className="p-3">{r.lead_time_days == null ? "—" : `${r.lead_time_days}d`}</td>
              <td className={cn("p-3", isLate(r.order_by) && "font-medium text-destructive")}>
                {fmt(r.order_by)}
                {isLate(r.order_by) && <Badge variant="destructive" className="ml-2">order now</Badge>}
              </td>
            </tr>
          ))}
        </tbody>
      </Section>
    </div>
  );
}

export default RequirementsPage;
