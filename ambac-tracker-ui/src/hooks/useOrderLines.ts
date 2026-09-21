/** Demand lines on an order, and turning one into work.
 *
 *  `Orders` records the customer engagement; a line records what they actually asked
 *  for. Before lines existed, quantity and part type lived only on a WorkOrder — i.e.
 *  only after somebody had already decided by hand what to build — so an order could be
 *  attached to work after the fact but could never produce it.
 */
import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/generated";
import { matchKey } from "@/lib/query-filters";

export type OrderLine = {
  id: string;
  order: string;
  line_number: number;
  part_type: string;
  part_type_name: string;
  quantity: number;
  /** Units already covered by non-cancelled work orders pegged to this line. */
  planned_quantity: number;
  /** Demand not yet turned into work. Derived, never stored — a counter would have to
   *  stay correct across work-order create, cancel, split and quantity change. */
  remaining_quantity: number;
  due_date: string | null;
  status: "OPEN" | "CANCELLED";
  notes: string;
};

export const orderLinesOptions = (orderId: string) =>
  queryOptions({
    queryKey: ["order-lines", orderId] as const,
    queryFn: () => api.api_OrderLines_list({
      queries: { order: orderId, limit: 200, ordering: "line_number" },
    } as never) as Promise<{ results: OrderLine[] }>,
    enabled: !!orderId,
  });

export function useOrderLines(orderId: string) {
  return useQuery(orderLinesOptions(orderId));
}

/** Add a demand line to an order.
 *
 *  `line_number` is the customer's own numbering, so it is supplied rather than
 *  auto-assigned — but the caller shouldn't have to think about it for the common case,
 *  so the panel passes "one past the highest line already there". */
export function useCreateOrderLine(orderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: {
      line_number: number; part_type: string; quantity: number;
      due_date?: string | null; notes?: string;
    }) => api.api_OrderLines_create({ order: orderId, ...v } as never),
    onSuccess: () => {
      qc.invalidateQueries(matchKey(["order-lines", orderId]));
      toast.success("Line added");
    },
    onError: (e: unknown) => {
      const d = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
      // DRF field errors come back keyed by field; surfacing the first one beats
      // "couldn't save", which tells the user nothing about which box to fix.
      const first = d && Object.entries(d)[0];
      toast.error(first ? `${first[0]}: ${String(first[1])}` : "Couldn't add the line");
    },
  });
}

/** Cancel a line. Not a delete: a line is a record of something a customer asked for,
 *  and the fact they asked survives the fact we are not going to build it. */
export function useCancelOrderLine(orderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.api_OrderLines_partial_update({ status: "CANCELLED" } as never,
                                        { params: { id } } as never),
    onSuccess: () => {
      qc.invalidateQueries(matchKey(["order-lines", orderId]));
      toast.success("Line cancelled");
    },
    onError: () => toast.error("Couldn't cancel the line"),
  });
}

/** Create a work order covering a line's remaining demand.
 *
 *  Refused with a reason rather than guessing when the part type has no approved
 *  routing or has several — releasing against the wrong one produces a correct-looking
 *  job that builds the wrong thing. */
export function usePlanOrderLine(orderId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity?: number }) =>
      api.api_OrderLines_plan_create(
        (quantity != null ? { quantity } : {}) as never,
        { params: { id } } as never,
      ) as Promise<{
        work_order_id: string; work_order_erp_id: string;
        quantity: number; remaining_quantity: number;
      }>,
    onSuccess: (r) => {
      qc.invalidateQueries(matchKey(["order-lines", orderId]));
      // New work changes what the board, the order and every planning surface show.
      qc.invalidateQueries(matchKey(["work-orders"]));
      qc.invalidateQueries(matchKey(["planning"]));
      toast.success(
        `${r.work_order_erp_id} created for ${r.quantity}` +
        (r.remaining_quantity > 0 ? ` · ${r.remaining_quantity} still unplanned` : ""),
      );
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      toast.error(detail ?? "Couldn't plan this line");
    },
  });
}
