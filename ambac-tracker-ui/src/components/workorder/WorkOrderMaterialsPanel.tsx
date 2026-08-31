/** "What this job needs" — per-work-order material requirements (picklist-lite).
 *
 * Top-level BOM components × the WO quantity, bucketed by the operation that consumes
 * them, with a shortage flag vs on-hand + promised. NOT a warehouse pick list: no bins,
 * lot selection, or reservations (that's the ERP/WMS's job). This tells the material
 * handler / sourcing what a job needs and whether it's covered.
 */
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useWorkOrderMaterialRequirements } from "@/hooks/useScheduling";
import { cn } from "@/lib/utils";

const STATUS: Record<string, { label: string; className: string }> = {
  ok: { label: "On hand", className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300" },
  building: { label: "Building", className: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
  short: { label: "Short", className: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" },
};

const num = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

const fmtDate = (d: string | null) =>
  d ? new Date(d + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" }) : null;

const todayISO = new Date().toISOString().slice(0, 10);

export function WorkOrderMaterialsPanel({ workOrderId }: { workOrderId: string }) {
  const { data, isLoading } = useWorkOrderMaterialRequirements(workOrderId);
  const rows = data ?? [];
  const shortCount = rows.filter((r) => r.status === "short").length;

  if (isLoading) {
    return <div className="h-40 animate-pulse rounded bg-muted" />;
  }

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No bill of materials for this work order's part type — nothing to stage. Author a BOM on
        the Part Type to see material requirements here.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Components this job consumes, by operation. Coverage is net of on-hand + promised
          receipts — a flag, not a reservation.
        </p>
        {shortCount > 0 && (
          <Badge variant="destructive">{shortCount} short</Badge>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Component</TableHead>
              <TableHead>Src</TableHead>
              <TableHead className="text-right">Need</TableHead>
              <TableHead className="text-right">On hand</TableHead>
              <TableHead className="text-right">Incoming</TableHead>
              <TableHead className="text-right">Short</TableHead>
              <TableHead>Consumed at</TableHead>
              <TableHead>Order by</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, i) => {
              const s = STATUS[r.status] ?? STATUS.short;
              return (
                <TableRow key={i} className={cn(r.is_optional && "text-muted-foreground")}>
                  <TableCell className="font-medium">
                    {r.component}
                    {r.is_optional && <span className="ml-1 text-xs">(optional)</span>}
                  </TableCell>
                  <TableCell>
                    <Badge variant={r.kind === "BUY" ? "outline" : "secondary"}>
                      {r.kind === "BUY" ? "Buy" : "Make"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(r.quantity)} {r.unit_of_measure}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{num(r.on_hand)}</TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">
                    {r.incoming > 0 ? num(r.incoming) : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {r.short_qty > 0 ? (
                      <span className="font-medium text-destructive">{num(r.short_qty)}</span>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {r.consumed_at_step || "Whole assembly"}
                  </TableCell>
                  <TableCell className={cn(r.order_by && r.order_by < todayISO && "font-medium text-destructive")}>
                    {r.order_by ? (
                      <span>
                        {fmtDate(r.order_by)}
                        {r.lead_time_days != null && (
                          <span className="ml-1 text-xs text-muted-foreground">({r.lead_time_days}d lead)</span>
                        )}
                        {r.order_by < todayISO && <Badge variant="destructive" className="ml-2">now</Badge>}
                      </span>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <span className={cn("rounded px-2 py-0.5 text-xs font-medium", s.className)}>
                      {s.label}
                    </span>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        “Incoming” = promised receipts for bought items, or quantity on live component work
        orders for made items. Bins, lot picking, and reservations live in the ERP.
      </p>
    </div>
  );
}

export default WorkOrderMaterialsPanel;
