import { TimeApprovalCard } from "@/components/scheduling/TimeApprovalCard";
import { usePermissionSet } from "@/hooks/useMyPermissions";
/** Operator Hours (/production/labor-hours).
 *
 * Shop hours worked per operator over a date range:
 *  - On-shift hrs    = attendance from the clock (clock-in→out, breaks excluded)
 *  - Direct hrs      = time on the operator's step records, inside on-shift time,
 *                      concurrent jobs shared, holds / outside processing left out
 *  - Rework hrs      = the part of direct spent on re-visits or rework steps
 *  - Unallocated hrs = on-shift − direct
 * Plus the same time by work order — the costing hand-off to the ERP (UQMES doesn't
 * price it). Scoped to shop-floor operators (Operator / Shift Lead). Server logic:
 * services/mes/labor_report.py.
 */
import { useState } from "react";
import { Clock, Download } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ReportButton } from "@/components/reports/ReportButton";
import { useOperatorHours, useWorkOrderHours } from "@/hooks/useScheduling";
import { downloadCsv } from "@/lib/csv";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const sum = <T,>(rows: T[], f: (r: T) => number) => rows.reduce((a, r) => a + f(r), 0);

export function LaborHoursPage() {
  const [start, setStart] = useState(iso(new Date(Date.now() - 7 * 86_400_000)));
  const [end, setEnd] = useState(iso(new Date()));
  const { data, isLoading } = useOperatorHours(start, end);
  const { data: woData, isLoading: woLoading } = useWorkOrderHours(start, end);
  const perms = usePermissionSet();
  const canApproveTime = perms.has("approve_timeentry");
  const canExport = perms.has("export_data");
  const rows = Array.isArray(data) ? data : [];
  const woRows = Array.isArray(woData) ? woData : [];
  const totalShift = sum(rows, (r) => r.on_shift_hours);
  const totalDirect = sum(rows, (r) => r.direct_hours);
  const totalRework = sum(rows, (r) => r.rework_hours);
  const totalUnallocated = sum(rows, (r) => r.unallocated_hours);

  const exportCsv = () =>
    downloadCsv(
      `operator_hours_${start}_${end}`,
      ["Operator", "On-shift hours", "Direct hours", "Rework hours", "Unallocated hours"],
      [
        ...rows.map((r) => [r.name, r.on_shift_hours.toFixed(2), r.direct_hours.toFixed(2),
                            r.rework_hours.toFixed(2), r.unallocated_hours.toFixed(2)]),
        ["Total", totalShift.toFixed(2), totalDirect.toFixed(2), totalRework.toFixed(2),
         totalUnallocated.toFixed(2)],
      ]
    );

  const woExportHref = (format: "csv" | "xlsx") =>
    `/api/Schedules/work_order_hours/export/${format}/?start=${start}&end=${end}`;

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary">
            <Clock className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Operator Hours</h1>
            <p className="text-sm text-muted-foreground">
              Shop hours per operator — on-shift attendance, and the time on their step
              records. Shop-floor operators only (Operator / Shift Lead).
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
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          [totalShift, "Total on-shift hours"],
          [totalDirect, "Total direct (job) hours"],
          [totalRework, "of which rework"],
          [totalUnallocated, "Unallocated hours"],
        ].map(([v, label]) => (
          <Card key={label as string}>
            <CardContent className="p-4">
              <div className="text-3xl font-semibold tabular-nums">{(v as number).toFixed(1)}</div>
              <div className="text-sm text-muted-foreground">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Per operator */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-muted-foreground">
              <th className="p-3 font-medium">Operator</th>
              <th className="p-3 text-right font-medium">On-shift hrs</th>
              <th className="p-3 text-right font-medium">Direct hrs</th>
              <th className="p-3 text-right font-medium">Rework hrs</th>
              <th className="p-3 text-right font-medium">Unallocated hrs</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={5}>Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={5}>No hours logged in this range.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.user_id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="p-3 font-medium">{r.name}</td>
                  <td className="p-3 text-right tabular-nums">{r.on_shift_hours.toFixed(1)}</td>
                  <td className="p-3 text-right tabular-nums">{r.direct_hours.toFixed(1)}</td>
                  <td className="p-3 text-right tabular-nums text-muted-foreground">{r.rework_hours.toFixed(1)}</td>
                  <td className="p-3 text-right tabular-nums text-muted-foreground">{r.unallocated_hours.toFixed(1)}</td>
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
                <td className="p-3 text-right tabular-nums">{totalRework.toFixed(1)}</td>
                <td className="p-3 text-right tabular-nums">{totalUnallocated.toFixed(1)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {/* Per work order — the costing hand-off */}
      <div className="rounded-lg border">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b p-3">
          <div>
            <div className="font-medium">By work order</div>
            <div className="text-xs text-muted-foreground">
              The same direct time, split by work order — for costing in the system that prices it.
            </div>
          </div>
          {canExport && (
            <div className="flex items-center gap-2">
              <Button asChild variant="outline" size="sm" disabled={woRows.length === 0}>
                <a href={woExportHref("csv")} download><Download className="mr-1.5 h-4 w-4" /> CSV</a>
              </Button>
              <Button asChild variant="outline" size="sm" disabled={woRows.length === 0}>
                <a href={woExportHref("xlsx")} download><Download className="mr-1.5 h-4 w-4" /> Excel</a>
              </Button>
            </div>
          )}
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-muted-foreground">
              <th className="p-3 font-medium">Work order</th>
              <th className="p-3 font-medium">Operator</th>
              <th className="p-3 text-right font-medium">Direct hrs</th>
              <th className="p-3 text-right font-medium">Rework hrs</th>
            </tr>
          </thead>
          <tbody>
            {woLoading ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={4}>Loading…</td></tr>
            ) : woRows.length === 0 ? (
              <tr><td className="p-3 text-muted-foreground" colSpan={4}>No job time in this range.</td></tr>
            ) : (
              woRows.map((r) => (
                <tr key={`${r.work_order_id}-${r.user_id}`} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="p-3 font-mono text-xs">{r.work_order}</td>
                  <td className="p-3">{r.name}</td>
                  <td className="p-3 text-right tabular-nums">{r.direct_hours.toFixed(2)}</td>
                  <td className="p-3 text-right tabular-nums text-muted-foreground">{r.rework_hours.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {canApproveTime && <TimeApprovalCard start={start} end={end} />}

      <p className="text-xs text-muted-foreground">
        On-shift = clock-in→out attendance (breaks excluded). Direct = time on the operator's
        step records, counted only while on shift; work running at the same time is shared
        between the jobs, not added up; time a job sat on hold or out for outside processing
        doesn't count. Rework (a re-visit, or a rework step) is part of direct. Hours data
        for payroll and costing to consume — not a payroll or cost calculation.
      </p>
    </div>
  );
}

export default LaborHoursPage;
