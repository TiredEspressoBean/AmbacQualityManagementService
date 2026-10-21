/** "For order" on a core receipt: the customer's open orders. Required for a
 *  repair-and-return core (its own unit is repaired against the order), optional for an
 *  exchange core. The server enforces the same rule (`receipt_order_refusal`). */
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useRetrieveOrders } from "@/hooks/useRetrieveOrders";
import { cn } from "@/lib/utils";

export const ORDER_NONE = "__none__";
const CLOSED = new Set(["COMPLETED", "CANCELLED"]);

export function CoreOrderSelect({ companyId, value, onChange, required, className }: {
    companyId: string | null;
    value: string;
    onChange: (v: string) => void;
    required: boolean;
    className?: string;
}) {
    const { data } = useRetrieveOrders(
        { company: companyId ?? undefined, archived: false, limit: 100 },
        undefined,
        { enabled: !!companyId },
    );
    const orders = (data?.results ?? []).filter((o) => !CLOSED.has(String(o.order_status)));
    const missing = required && (!value || value === ORDER_NONE);
    return (
        <Select value={value || ORDER_NONE} onValueChange={onChange} disabled={!companyId}>
            <SelectTrigger className={cn(className, missing && "border-destructive")}
                           aria-label="For order" aria-invalid={missing}>
                <SelectValue placeholder="For order" />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value={ORDER_NONE}>
                    {!companyId ? "Pick a customer first" : required ? "Pick the order…" : "No order"}
                </SelectItem>
                {orders.map((o) => (
                    <SelectItem key={o.id} value={String(o.id)}>
                        {o.order_number} · {o.name}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
