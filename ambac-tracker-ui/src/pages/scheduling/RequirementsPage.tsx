/** Sourcing & production requirements report (/production/requirements).
 *
 * What open demand needs, so purchasing/receiving and production know what to act on
 * and by when. Three lanes (source / produce / tooling) with lead-time-driven order-by
 * dates; rows past their order-by are flagged. Export to spreadsheet (CSV) or PDF.
 */
import { ClipboardList, Download } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReportButton } from "@/components/reports/ReportButton";
import { useRequirements } from "@/hooks/useScheduling";
import { downloadCsv } from "@/lib/csv";
import { cn } from "@/lib/utils";

const fmt = (d: string | null) =>
  d ? new Date(d + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";

const todayISO = new Date().toISOString().slice(0, 10);
const isLate = (orderBy: string | null) => !!orderBy && orderBy < todayISO;

function Section({
  title, subtitle, children, empty, count,
}: {
  title: string; subtitle: string; children: React.ReactNode; empty: boolean; count: number;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <span className="text-xs text-muted-foreground">{count} item{count === 1 ? "" : "s"}</span>
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

  const exportCsv = () =>
    downloadCsv(
      `requirements_${todayISO}`,
      ["Lane", "Item", "Kind / Component", "Qty", "Need by", "Order by", "Notes"],
      [
        ...source.map((r) => ["Source", r.material, "Buy", r.qty_short, r.need_by ?? "", r.order_by ?? "",
          r.incoming_date ? `incoming ${r.incoming_date}` : ""]),
        ...produce.map((r) => ["Produce", r.component, r.work_order, r.qty, r.need_by ?? "", "", r.status]),
        ...tooling.map((r) => ["Tooling", r.fixture, r.kind, "", "", r.order_by ?? "", ""]),
      ]
    );

  const anyRows = source.length + produce.length + tooling.length > 0;

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
      >
        <thead>
          <tr className="border-b bg-muted/40 text-left text-muted-foreground">
            <th className="p-3 font-medium">Material</th>
            <th className="p-3 text-right font-medium">Short</th>
            <th className="p-3 font-medium">Lead time</th>
            <th className="p-3 font-medium">Need by</th>
            <th className="p-3 font-medium">Order by</th>
            <th className="p-3 font-medium">Incoming</th>
          </tr>
        </thead>
        <tbody>
          {source.map((r, i) => (
            <tr key={i} className="border-b last:border-0 hover:bg-muted/30">
              <td className="p-3 font-medium">{r.material}</td>
              <td className="p-3 text-right tabular-nums">{r.qty_short}</td>
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
