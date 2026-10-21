/**
 * Production › Orders — the open order book. One row per open order, including orders
 * with no work orders yet (the ones a planner needs to see first), with what's
 * unplanned, projected finish against the promise, and what's blocking it.
 * Demand, progress and promises only — nothing financial.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ListOrdered } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { parseDateOnly } from "@/lib/date-only";
import { useOrderBook } from "@/hooks/useOrderBook";
import { BlockerChips, ProgressBar, ProjectionText } from "@/components/orders/OrderBookBits";

const ANY = "any";

export function OrderBookPage() {
    const navigate = useNavigate();
    const { data, isLoading } = useOrderBook();
    const [customer, setCustomer] = useState(ANY);
    const [dueWithin, setDueWithin] = useState(ANY);
    const [atRisk, setAtRisk] = useState(false);
    const [needsPlanning, setNeedsPlanning] = useState(false);

    const rows = useMemo(() => data?.rows ?? [], [data]);
    const customers = useMemo(
        () => [...new Set(rows.map((r) => r.customer_name).filter((c): c is string => !!c))].sort(),
        [rows]);
    const shown = useMemo(() => {
        const today = new Date();
        return rows.filter((r) => {
            if (customer !== ANY && r.customer_name !== customer) return false;
            if (atRisk && !r.at_risk) return false;
            if (needsPlanning && r.unplanned === 0) return false;
            if (dueWithin !== ANY) {
                if (!r.earliest_due) return false;
                const days = (parseDateOnly(r.earliest_due).getTime() - today.getTime()) / 86_400_000;
                if (days > Number(dueWithin)) return false;
            }
            return true;
        });
    }, [rows, customer, atRisk, needsPlanning, dueWithin]);

    const otd = data?.on_time;

    return (
        <div className="mx-auto max-w-7xl space-y-4 p-6">
            <div className="flex flex-wrap items-center gap-3">
                <ListOrdered className="h-6 w-6 text-muted-foreground" />
                <h1 className="text-2xl font-semibold tracking-tight">Orders</h1>
                {otd && (
                    <div className="ml-auto rounded-md border px-3 py-2 text-sm">
                        <span className="text-muted-foreground">On time, last {otd.days} days: </span>
                        <span className="font-semibold tabular-nums">
                            {otd.on_time_pct != null ? `${otd.on_time_pct}%` : "—"}
                        </span>
                        {otd.deliveries > 0 && (
                            <span className="text-muted-foreground"> ({otd.on_time} of {otd.deliveries})</span>
                        )}
                        {otd.unmeasured > 0 && (
                            <span className="text-amber-600"
                                  title="Shipped work orders with no order-line due date and no expected completion. They can't be scored on time, so they're excluded from the percentage.">
                                {" "}· {otd.unmeasured} not measurable
                            </span>
                        )}
                    </div>
                )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm">
                <Select value={customer} onValueChange={setCustomer}>
                    <SelectTrigger className="w-56" aria-label="Customer"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ANY}>All customers</SelectItem>
                        {customers.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Select value={dueWithin} onValueChange={setDueWithin}>
                    <SelectTrigger className="w-44" aria-label="Due within"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value={ANY}>Any due date</SelectItem>
                        <SelectItem value="7">Due within 7 days</SelectItem>
                        <SelectItem value="14">Due within 14 days</SelectItem>
                        <SelectItem value="30">Due within 30 days</SelectItem>
                    </SelectContent>
                </Select>
                <Label className="flex items-center gap-2 font-normal">
                    <Checkbox checked={atRisk} onCheckedChange={(v) => setAtRisk(v === true)} /> At risk
                </Label>
                <Label className="flex items-center gap-2 font-normal">
                    <Checkbox checked={needsPlanning} onCheckedChange={(v) => setNeedsPlanning(v === true)} /> Needs planning
                </Label>
                <span className="text-muted-foreground">{shown.length} of {rows.length} open orders</span>
            </div>

            {isLoading ? (
                <Skeleton className="h-64 w-full" />
            ) : shown.length === 0 ? (
                <p className="rounded-lg border p-4 text-sm text-muted-foreground">No open orders match.</p>
            ) : (
                <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/40 text-xs text-muted-foreground">
                            <tr>
                                <th className="px-3 py-2 text-left font-medium">Order</th>
                                <th className="px-3 py-2 text-left font-medium">Customer</th>
                                <th className="px-3 py-2 text-left font-medium">Earliest due</th>
                                <th className="px-3 py-2 text-left font-medium">Planning</th>
                                <th className="px-3 py-2 text-left font-medium">Projected vs promised</th>
                                <th className="px-3 py-2 text-left font-medium">Blocked by</th>
                                <th className="px-3 py-2 text-left font-medium">Progress</th>
                            </tr>
                        </thead>
                        <tbody>
                            {shown.map((r) => (
                                <tr key={r.order_id}
                                    className="cursor-pointer border-t hover:bg-accent/40"
                                    onClick={() => navigate({ to: "/production/orders/$orderId", params: { orderId: r.order_id } })}>
                                    <td className="px-3 py-2">
                                        <div className="font-mono text-xs">{r.order_number}</div>
                                        <div className="text-muted-foreground">{r.name}</div>
                                    </td>
                                    <td className="px-3 py-2">{r.customer_name ?? "—"}</td>
                                    <td className="px-3 py-2 tabular-nums">
                                        {r.earliest_due ? parseDateOnly(r.earliest_due).toLocaleDateString() : "—"}
                                    </td>
                                    <td className="px-3 py-2">
                                        {r.unplanned > 0
                                            ? <Badge variant="outline" className="border-amber-500/60 text-amber-700 dark:text-amber-400">{r.unplanned} unplanned</Badge>
                                            : <span className="text-xs text-muted-foreground">planned</span>}
                                    </td>
                                    <td className="px-3 py-2"><ProjectionText p={r.projection} /></td>
                                    <td className="px-3 py-2"><BlockerChips blockers={r.blockers} more={r.more_blockers} /></td>
                                    <td className="px-3 py-2"><ProgressBar p={r.progress} /></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
