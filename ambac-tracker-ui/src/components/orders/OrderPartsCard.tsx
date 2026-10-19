import { useState } from "react";
import { queryOptions, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { apiErrorMessage } from "@/lib/api/describeApiError";
import { useRemovePartsMutation } from "@/hooks/useRemovePartsMutation";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const orderPartsOptions = (orderId: string) =>
    queryOptions({
        queryKey: ["order-parts", orderId] as const,
        queryFn: () => api.api_Parts_list({ queries: { order: orderId, limit: 500 } }),
    });

/**
 * The parts on a customer order, for staff who maintain orders. Removing a part takes
 * it off this order only — it stays on its work order, at its step, in its status
 * (services/mes/orders.remove_parts_from_order).
 */
export function OrderPartsCard({ orderId }: { orderId: string }) {
    const queryClient = useQueryClient();
    const { data, isLoading } = useQuery(orderPartsOptions(orderId));
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [confirmOpen, setConfirmOpen] = useState(false);
    const parts = data?.results ?? [];

    const remove = useRemovePartsMutation({ orderId }, {
        meta: { suppressGlobalError: true },
        onSuccess: (result) => {
            const n = (result as { removed?: number }).removed ?? selected.size;
            toast.success(`Removed ${n} part${n === 1 ? "" : "s"} from the order`);
            setSelected(new Set());
            // The parts list and the order page both key on the order id.
            queryClient.invalidateQueries({ predicate: (q) => JSON.stringify(q.queryKey).includes(orderId) });
        },
        onError: (e) => toast.error(apiErrorMessage(e) ?? "Couldn't remove the parts"),
    });

    const toggle = (id: string) => setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id); else next.add(id);
        return next;
    });
    const allSelected = parts.length > 0 && selected.size === parts.length;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <CardTitle className="text-base">Parts on this order</CardTitle>
                        <CardDescription>{isLoading ? "Loading…" : `${parts.length} part${parts.length === 1 ? "" : "s"}`}</CardDescription>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        disabled={selected.size === 0 || remove.isPending}
                        onClick={() => setConfirmOpen(true)}
                    >
                        Remove from order{selected.size > 0 ? ` (${selected.size})` : ""}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {parts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">{isLoading ? "" : "No parts are on this order."}</p>
                ) : (
                    <table className="w-full text-sm">
                        <thead className="text-left text-xs text-muted-foreground">
                            <tr>
                                <th className="w-8 py-1">
                                    <Checkbox
                                        checked={allSelected}
                                        onCheckedChange={() => setSelected(allSelected ? new Set() : new Set(parts.map((p) => p.id)))}
                                        aria-label="Select all"
                                    />
                                </th>
                                <th className="py-1">Part</th>
                                <th className="py-1">Type</th>
                                <th className="py-1">Step</th>
                                <th className="py-1">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {parts.map((p) => (
                                <tr key={p.id} className="border-t">
                                    <td className="py-1">
                                        <Checkbox checked={selected.has(p.id)} onCheckedChange={() => toggle(p.id)} aria-label={`Select ${p.ERP_id}`} />
                                    </td>
                                    <td className="py-1 font-mono">{p.ERP_id}</td>
                                    <td className="py-1">{p.part_type_name ?? "—"}</td>
                                    <td className="py-1">{p.step_name ?? "—"}</td>
                                    <td className="py-1 text-xs">{(p.part_status ?? "").replace(/_/g, " ").toLowerCase()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </CardContent>

            <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Remove {selected.size} part{selected.size === 1 ? "" : "s"} from this order?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Only the link to this customer order is removed. The parts stay on their work
                            orders, at their current step and status, and no longer count toward this order.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => remove.mutate(Array.from(selected))}>
                            Remove from order
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    );
}
