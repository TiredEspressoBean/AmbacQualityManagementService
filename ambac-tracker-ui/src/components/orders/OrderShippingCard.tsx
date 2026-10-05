import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { orderShippingOptions } from "@/hooks/useShipping";

const STATE: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
    OPEN: { label: "Not shipped", variant: "outline" },
    PART_SHIPPED: { label: "Part shipped", variant: "secondary" },
    SHIPPED: { label: "Shipped", variant: "default" },
};

/**
 * How much of each order line has gone, on which shipments, and whether each went by
 * the line's due date. Hidden for orders without lines, and for viewers who can't see
 * shipments (the endpoint answers 403 and the card stays away).
 */
export function OrderShippingCard({ orderId }: { orderId: string }) {
    const { data } = useQuery({ ...orderShippingOptions(orderId), retry: false });
    if (!data || data.lines.length === 0) return null;

    return (
        <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">Shipping</CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b text-left text-muted-foreground">
                            <th className="py-2 pr-3 font-medium">Line</th>
                            <th className="py-2 pr-3 font-medium">Item</th>
                            <th className="py-2 pr-3 text-right font-medium">Shipped</th>
                            <th className="py-2 pr-3 font-medium">Due</th>
                            <th className="py-2 font-medium">Shipments</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.lines.map((l) => (
                            <tr key={l.line_id} className="border-b align-top last:border-0">
                                <td className="py-2 pr-3 tabular-nums">{l.line_number}</td>
                                <td className="py-2 pr-3">{l.part_type}</td>
                                <td className="py-2 pr-3 text-right tabular-nums">
                                    {l.shipped} / {l.ordered}
                                    <div><Badge variant={STATE[l.state]?.variant ?? "outline"}>{STATE[l.state]?.label ?? l.state}</Badge></div>
                                </td>
                                <td className="py-2 pr-3 tabular-nums">{l.due_date ?? "—"}</td>
                                <td className="py-2">
                                    {l.shipments.length === 0 ? <span className="text-muted-foreground">—</span> : (
                                        <div className="flex flex-wrap gap-1.5">
                                            {l.shipments.map((s) => (
                                                <Link key={s.shipment_id} to="/production/shipments/$shipmentId" params={{ shipmentId: s.shipment_id }}>
                                                    <Badge variant="outline" className={s.on_time ? "" : "border-destructive text-destructive"}>
                                                        {s.shipment_number} · {s.quantity} · {new Date(s.shipped_at).toLocaleDateString()}{s.on_time ? "" : " · late"}
                                                    </Badge>
                                                </Link>
                                            ))}
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </CardContent>
        </Card>
    );
}
