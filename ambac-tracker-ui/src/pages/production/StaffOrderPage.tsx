/**
 * Production › Orders › one order — the staff page: the promise, the lines (planned
 * here, with a capacity check), the work orders and their projections, shipments
 * judged on time, and the notes. The customer-facing /orders page stays read-only.
 * Demand, progress and promises only — nothing financial.
 */
import { useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/generated";
import { parseDateOnly } from "@/lib/date-only";
import { OrderLinesPanel } from "@/components/orders/OrderLinesPanel";
import { BlockerChips, ProgressBar, ProjectionText } from "@/components/orders/OrderBookBits";
import { useOrderBookDetail } from "@/hooks/useOrderBook";
import { useOrderDetails } from "@/hooks/useOrderDetails";
import { usePermissionSet } from "@/hooks/useMyPermissions";

const day = (d: string | null | undefined) => (d ? parseDateOnly(d).toLocaleDateString() : "—");

export function StaffOrderPage() {
    const { orderId } = useParams({ from: "/production/orders/$orderId" });
    const { data: book, isLoading, refetch: refetchBook } = useOrderBookDetail(orderId);
    const { data: order, refetch: refetchOrder } = useOrderDetails(orderId);
    const canEdit = usePermissionSet().has("change_orders");
    const [note, setNote] = useState("");
    const addNote = useMutation({
        mutationFn: (message: string) =>
            api.api_Orders_add_note_create({ message, visibility: "INTERNAL" }, { params: { id: orderId } }),
        onSuccess: () => { setNote(""); void refetchOrder(); },
    });

    if (isLoading || !book) return <div className="p-6"><Skeleton className="h-64 w-full" /></div>;
    const row = book.row;
    const moved = book.original_completion && book.estimated_completion
        && book.original_completion !== book.estimated_completion;

    return (
        <div className="mx-auto max-w-6xl space-y-4 p-6">
            <Link to="/production/orders" className="inline-flex items-center text-sm text-muted-foreground hover:underline">
                <ArrowLeft className="mr-1 h-4 w-4" /> Orders
            </Link>

            <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                    <div className="font-mono text-xs text-muted-foreground">{row.order_number}</div>
                    <h1 className="text-2xl font-semibold tracking-tight">{row.name}</h1>
                    <div className="text-sm text-muted-foreground">
                        {row.customer_name ?? "No customer"}
                        {order?.customer_first_name ? ` · ${order.customer_first_name} ${order.customer_last_name ?? ""}` : ""}
                        {order?.order_status ? ` · ${order.order_status}` : ""}
                    </div>
                </div>
                {canEdit && (
                    <Button variant="outline" asChild>
                        <Link to="/editor/orders/$id/edit" params={{ id: orderId }}>
                            <Pencil className="mr-1.5 h-4 w-4" /> Edit order
                        </Link>
                    </Button>
                )}
            </div>

            <Card>
                <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-6 text-sm">
                    <div>
                        <span className="text-muted-foreground">Promised: </span>
                        <b>{day(book.estimated_completion)}</b>
                        {moved && <span className="text-muted-foreground"> (originally {day(book.original_completion)})</span>}
                    </div>
                    <ProjectionText p={row.projection} />
                    <BlockerChips blockers={row.blockers} more={row.more_blockers} />
                    <div className="ml-auto"><ProgressBar p={row.progress} /></div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Lines</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                    {/* Planning happens here: Plan N / cancel line / Add line. */}
                    <OrderLinesPanel orderId={orderId} />
                    {book.lines.length > 0 && (
                        <table className="w-full text-sm">
                            <thead className="text-xs text-muted-foreground">
                                <tr>
                                    <th className="py-1 text-left font-medium">Line</th>
                                    <th className="py-1 text-left font-medium">Item</th>
                                    <th className="py-1 text-left font-medium">Due</th>
                                    <th className="py-1 text-left font-medium">Progress</th>
                                    <th className="py-1 text-right font-medium" />
                                </tr>
                            </thead>
                            <tbody>
                                {book.lines.map((ln) => (
                                    <tr key={ln.line_id} className="border-t">
                                        <td className="py-1.5">L{ln.line_number}</td>
                                        <td className="py-1.5">{ln.quantity} × {ln.part_type_name}
                                            {ln.remaining > 0 && (
                                                <Badge variant="outline" className="ml-2 border-amber-500/60 text-amber-700 dark:text-amber-400">
                                                    {ln.remaining} unplanned
                                                </Badge>
                                            )}
                                        </td>
                                        <td className="py-1.5 tabular-nums">{day(ln.due_date)}</td>
                                        <td className="py-1.5"><ProgressBar p={ln.progress} /></td>
                                        <td className="py-1.5 text-right">
                                            {ln.status === "OPEN" && (
                                                <Button type="button" size="sm" variant="ghost" asChild>
                                                    <Link to="/production/capacity" search={{
                                                        tab: "simulator", part_type: ln.part_type_id,
                                                        quantity: Math.max(ln.remaining, 1),
                                                        ...(ln.due_date ? { due: ln.due_date } : {}),
                                                    }}>
                                                        <CalendarClock className="mr-1 h-4 w-4" /> Check capacity
                                                    </Link>
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Work orders</CardTitle></CardHeader>
                <CardContent>
                    {book.work_orders.length === 0 ? (
                        <p className="text-sm text-muted-foreground">None yet — plan the lines above.</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead className="text-xs text-muted-foreground">
                                <tr>
                                    <th className="py-1 text-left font-medium">Work order</th>
                                    <th className="py-1 text-left font-medium">Status</th>
                                    <th className="py-1 text-left font-medium">Projected vs due</th>
                                    <th className="py-1 text-left font-medium">Blocked by</th>
                                </tr>
                            </thead>
                            <tbody>
                                {book.work_orders.map((w) => (
                                    <tr key={w.work_order_id} className="border-t">
                                        <td className="py-1.5">
                                            <Link to="/workorder/$workOrderId" params={{ workOrderId: w.work_order_id }}
                                                  className="font-mono text-xs text-primary hover:underline">{w.erp_id}</Link>
                                        </td>
                                        <td className="py-1.5">
                                            {w.status.replace(/_/g, " ").toLowerCase()}
                                            {!w.released && <Badge variant="outline" className="ml-2">not released</Badge>}
                                            {w.units.length > 0 && (
                                                <div className="text-xs text-muted-foreground">
                                                    This order's {w.units.join(", ")}
                                                </div>
                                            )}
                                        </td>
                                        <td className="py-1.5"><ProjectionText p={w.projection} /></td>
                                        <td className="py-1.5"><BlockerChips blockers={w.blockers} /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                        Shipments
                        {book.ready_to_ship > 0 && (
                            <Link to="/production/shipments" className="text-xs font-normal text-primary underline underline-offset-2">
                                {book.ready_to_ship} ready to ship → Shipping
                            </Link>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {book.shipments.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Nothing shipped yet.</p>
                    ) : (
                        <table className="w-full text-sm">
                            <thead className="text-xs text-muted-foreground">
                                <tr>
                                    <th className="py-1 text-left font-medium">Shipment</th>
                                    <th className="py-1 text-left font-medium">Shipped</th>
                                    <th className="py-1 text-left font-medium">Line</th>
                                    <th className="py-1 text-right font-medium">Qty</th>
                                    <th className="py-1 text-right font-medium" />
                                </tr>
                            </thead>
                            <tbody>
                                {book.shipments.map((s) => (
                                    <tr key={`${s.shipment_id}-${s.line_number}`} className="border-t">
                                        <td className="py-1.5">
                                            <Link to="/production/shipments/$shipmentId" params={{ shipmentId: s.shipment_id }}
                                                  className="font-mono text-xs text-primary hover:underline">{s.shipment_number}</Link>
                                        </td>
                                        <td className="py-1.5 tabular-nums">{day(s.shipped_at)}</td>
                                        <td className="py-1.5">{s.line_number != null ? `L${s.line_number}` : "—"}</td>
                                        <td className="py-1.5 text-right tabular-nums">{s.quantity}</td>
                                        <td className="py-1.5 text-right">
                                            {s.on_time == null ? <span className="text-xs text-muted-foreground">no due date</span>
                                                : s.on_time ? <Badge variant="outline" className="border-green-600/50 text-green-700 dark:text-green-400">ON TIME</Badge>
                                                    : <Badge variant="destructive">LATE</Badge>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-base">Notes</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex gap-2">
                        <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                                  placeholder="An internal note on this order" />
                        <Button type="button" disabled={!note.trim() || addNote.isPending}
                                onClick={() => addNote.mutate(note.trim(), { onSettled: () => void refetchBook() })}>
                            Add
                        </Button>
                    </div>
                    {(order?.notes_timeline ?? []).length === 0 ? (
                        <p className="text-sm text-muted-foreground">No notes.</p>
                    ) : (
                        <ul className="space-y-2 text-sm">
                            {(order?.notes_timeline ?? []).map((n, i) => (
                                <li key={i} className="rounded border p-2">
                                    <div className="text-xs text-muted-foreground">
                                        {n.user} · {n.timestamp ? new Date(n.timestamp).toLocaleString() : ""}
                                        {n.visibility === "internal" && <Badge variant="outline" className="ml-2 text-[10px]">internal</Badge>}
                                    </div>
                                    <div className="whitespace-pre-wrap">{n.message}</div>
                                </li>
                            ))}
                        </ul>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
