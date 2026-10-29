/** Labor on this job to date — direct and rework hours per operator, derived from the
 * step records (the same logic as Operator Hours: only while on shift, concurrent work
 * shared, holds and outside processing left out), beside the route's planned operator
 * hours where its steps carry time standards.
 */
import { useWorkOrderLabor } from "@/hooks/useScheduling";
import { cn } from "@/lib/utils";

const h = (n: number) => n.toFixed(1);

export function WorkOrderLaborPanel({ workOrderId }: { workOrderId: string }) {
  const { data, isLoading } = useWorkOrderLabor(workOrderId);

  if (isLoading || !data) {
    return <div className="h-40 animate-pulse rounded bg-muted" />;
  }

  const planned = data.planned_hours;
  const over = planned != null && data.direct_hours > planned;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-md border p-3">
          <div className="text-2xl font-semibold tabular-nums">{h(data.direct_hours)}</div>
          <div className="text-xs text-muted-foreground">Actual direct hrs</div>
        </div>
        <div className="rounded-md border p-3">
          <div className="text-2xl font-semibold tabular-nums">{h(data.rework_hours)}</div>
          <div className="text-xs text-muted-foreground">of which rework</div>
        </div>
        <div className="rounded-md border p-3">
          <div className={cn("text-2xl font-semibold tabular-nums", over && "text-amber-600 dark:text-amber-400")}>
            {planned != null ? h(planned) : "—"}
          </div>
          <div className="text-xs text-muted-foreground">
            {planned != null ? "Planned hrs" : "No time standards on the route"}
          </div>
        </div>
      </div>

      {data.rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No work started on this job yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="p-2 font-medium">Operator</th>
              <th className="p-2 text-right font-medium">Direct hrs</th>
              <th className="p-2 text-right font-medium">Rework hrs</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.user_id} className="border-b last:border-0">
                <td className="p-2">{r.name}</td>
                <td className="p-2 text-right tabular-nums">{r.direct_hours.toFixed(2)}</td>
                <td className="p-2 text-right tabular-nums text-muted-foreground">{r.rework_hours.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="text-xs text-muted-foreground">
        From the step records: counted only while the operator was on shift, work running at
        the same time shared between jobs, and time on hold or out for outside processing
        left out. Rework is part of direct. Planned is the route's operator time for the
        work order quantity, from step time standards; rework steps aren't planned.
      </p>
    </div>
  );
}
