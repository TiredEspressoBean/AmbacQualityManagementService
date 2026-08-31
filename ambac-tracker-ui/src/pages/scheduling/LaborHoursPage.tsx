/** Operator Hours (/production/labor-hours).
 *
 * Shop hours worked per operator over a date range, from TimeEntry:
 *  - On-shift hrs = attendance (clock-in→out, breaks excluded)
 *  - Direct hrs   = time clocked onto jobs (production/setup/rework)
 * Scoped to shop-floor operators (Operator / Shift Lead groups). Payroll-facing:
 * export to spreadsheet (CSV) or a printable PDF.
 */
import { useState } from "react";
import { Clock, Download } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ReportButton } from "@/components/reports/ReportButton";
import { useOperatorHours } from "@/hooks/useScheduling";
import { downloadCsv } from "@/lib/csv";

const iso = (d: Date) => d.toISOString().slice(0, 10);

export function LaborHoursPage() {
  const [start, setStart] = useState(iso(new Date(Date.now() - 7 * 86_400_000)));
  const [end, setEnd] = useState(iso(new Date()));
  const { data, isLoading } = useOperatorHours(start, end);
  const rows = Array.isArray(data) ? data : [];
  const totalShift = rows.reduce((a, r) => a + r.on_shift_hours, 0);
  const totalDirect = rows.reduce((a, r) => a + r.direct_hours, 0);

  const exportCsv = () =>
    downloadCsv(
      `operator_hours_${start}_${end}`,
      ["Operator", "On-shift hours", "Direct hours"],
      [
        ...rows.map((r) => [r.name, r.on_shift_hours.toFixed(2), r.direct_hours.toFixed(2)]),
        ["Total", totalShift.toFixed(2), totalDirect.toFixed(2)],
      ]
    );

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary">
            <Clock className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Operator Hours</h1>
            <p className="text-sm text-muted-foreground">
              Shop hours per operator — on-shift attendance and time clocked onto jobs.
              Shop-floor operators only (Operator / Shift Lead).
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={rows.length === 0}>
            <Download className="mr-1.5 h-4 w-4" /> CSV
          </Button>
          <ReportButton
            reportType="labor_hours"
            label="PDF"
            allowEmail
            params={start && end ? { start, end } : null}
          />
        </div>
      </div>

      {/* Date range */}
      <div className="flex items-end gap-3">
        <div className="grid gap-1">
          <Label className="text-xs">From</Label>
          <Input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="grid gap-1">
          <Label className="text-xs">To</Label>
          <Input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-3xl font-semibold tabular-nums">{totalShift.toFixed(1)}</div>
            <div className="text-sm text-muted-foreground">Total on-shift hours</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-3xl font-semibold tabular-nums">{totalDirect.toFixed(1)}</div>
            <div className="text-sm text-muted-foreground">Total direct (job) hours</div>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-muted-foreground">
              <th className="p-3 font-medium">Operator</th>
              <th className="p-3 text-right font-medium">On-shift hrs</th>
              <th className="p-3 text-right font-medium">Direct hrs</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={3}>Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={3}>No hours logged in this range.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.user_id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="p-3 font-medium">{r.name}</td>
                  <td className="p-3 text-right tabular-nums">{r.on_shift_hours.toFixed(1)}</td>
                  <td className="p-3 text-right tabular-nums text-muted-foreground">{r.direct_hours.toFixed(1)}</td>
                </tr>
              ))
            )}
          </tbody>
          {rows.length > 0 && (
            <tfoot>
              <tr className="border-t bg-muted/40 font-semibold">
                <td className="p-3">Total</td>
                <td className="p-3 text-right tabular-nums">{totalShift.toFixed(1)}</td>
                <td className="p-3 text-right tabular-nums">{totalDirect.toFixed(1)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        On-shift = clock-in→out attendance (breaks excluded); direct = time clocked onto jobs.
        Hours data for payroll to consume — not a payroll calculation.
      </p>
    </div>
  );
}

export default LaborHoursPage;
