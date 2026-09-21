/** Demand lines on an order, and the button that turns one into work.
 *
 *  Named `OrderLinesPanel` rather than anything shorter because
 *  `components/order-line-item.tsx` already exists and means something else — a Part
 *  row in a list, "line item" as in list row. These are demand lines: what the customer
 *  asked for, before anyone decided how to build it.
 *
 *  `remaining` is the number worth looking at. An order with lines all showing 0
 *  remaining is fully planned; anything above 0 is demand nobody has committed capacity
 *  to yet, which is exactly the work that is invisible on the schedule.
 */
import { useState } from "react";
import { Loader2, PackagePlus, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  useCancelOrderLine, useCreateOrderLine, useOrderLines, usePlanOrderLine,
  type OrderLine,
} from "@/hooks/useOrderLines";
import { useRetrievePartTypes } from "@/hooks/useRetrievePartTypes";
import { usePermissionSet } from "@/hooks/useMyPermissions";

const fmtDate = (iso: string | null) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined,
    { month: "short", day: "numeric", year: "numeric" }) : "—";

/** Adding a line. Inline rather than a dialog: an order routinely has several lines and
 *  they get typed one after another, so a modal that has to be reopened per line is the
 *  wrong shape for the task. */
function AddLineForm({ orderId, nextLineNumber, onDone }: {
  orderId: string; nextLineNumber: number; onDone: () => void;
}) {
  const create = useCreateOrderLine(orderId);
  const { data: partTypesData } = useRetrievePartTypes({ limit: 200 } as never);
  const partTypes = partTypesData?.results ?? [];

  const [partType, setPartType] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [dueDate, setDueDate] = useState("");

  const submit = () => {
    const qty = Number(quantity);
    if (!partType || !Number.isFinite(qty) || qty <= 0) return;
    create.mutate(
      {
        line_number: nextLineNumber, part_type: partType, quantity: qty,
        due_date: dueDate || null,
      },
      { onSuccess: () => { setPartType(""); setQuantity("1"); setDueDate(""); onDone(); } },
    );
  };

  return (
    <tr className="border-t bg-muted/30">
      <td className="px-3 py-2 text-xs tabular-nums text-muted-foreground">
        {nextLineNumber}
      </td>
      <td className="px-3 py-2">
        <Select value={partType} onValueChange={setPartType}>
          <SelectTrigger className="h-8"><SelectValue placeholder="Part type…" /></SelectTrigger>
          <SelectContent>
            {partTypes.map((pt: { id: string; name: string }) => (
              <SelectItem key={pt.id} value={pt.id}>{pt.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </td>
      <td className="px-3 py-2">
        <Input className="h-8 w-20 text-right" type="number" min={1}
               value={quantity} onChange={(e) => setQuantity(e.target.value)} />
      </td>
      {/* Planned and Remaining are derived — nothing to type. */}
      <td className="px-3 py-2 text-right text-muted-foreground">—</td>
      <td className="px-3 py-2 text-right text-muted-foreground">—</td>
      <td className="px-3 py-2">
        <Input className="h-8" type="date" value={dueDate}
               onChange={(e) => setDueDate(e.target.value)} />
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1">
          <Button size="sm" onClick={submit}
                  disabled={!partType || create.isPending}>
            {create.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
            Add
          </Button>
          <Button size="sm" variant="ghost" onClick={onDone}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      </td>
    </tr>
  );
}

function LineRow({ line, orderId, canPlan, readOnly }: {
  line: OrderLine; orderId: string; canPlan: boolean; readOnly: boolean;
}) {
  const plan = usePlanOrderLine(orderId);
  const cancel = useCancelOrderLine(orderId);
  const [planning, setPlanning] = useState(false);
  const remaining = line.remaining_quantity;
  const cancelled = line.status === "CANCELLED";

  return (
    <tr className="border-t">
      <td className="px-3 py-2 text-xs tabular-nums text-muted-foreground">
        {line.line_number}
      </td>
      <td className="px-3 py-2">
        <span className={cancelled ? "line-through text-muted-foreground" : ""}>
          {line.part_type_name}
        </span>
        {cancelled && (
          <Badge variant="outline" className="ml-2 text-[10px]">Cancelled</Badge>
        )}
      </td>
      <td className="px-3 py-2 text-right tabular-nums">{line.quantity}</td>
      {/* Planned and Remaining are OUR scheduling state, not the customer's business:
          "12 of your 25 are planned" invites a question about the other 13 that the
          due date already answers. Shown to staff, hidden on the customer view. */}
      {!readOnly && (
        <>
          <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
            {line.planned_quantity}
          </td>
          <td className="px-3 py-2 text-right tabular-nums">
            {/* The one number that drives a decision, so it gets the colour. */}
            <span className={remaining > 0 && !cancelled
              ? "font-semibold text-amber-600 dark:text-amber-400"
              : "text-muted-foreground"}>
              {remaining}
            </span>
          </td>
        </>
      )}
      <td className="px-3 py-2 text-sm text-muted-foreground">{fmtDate(line.due_date)}</td>
      {!readOnly && (
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1">
          {canPlan && remaining > 0 && !cancelled && (
            <Button
              size="sm" variant="outline"
              disabled={planning}
              onClick={() => {
                setPlanning(true);
                plan.mutate({ id: line.id },
                  { onSettled: () => setPlanning(false) });
              }}
            >
              {planning
                ? <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                : <PackagePlus className="mr-1 h-3 w-3" />}
              Plan {remaining}
            </Button>
          )}
          {/* Cancelling is only offered while NOTHING has been planned. Once work
              exists the line is not a clean thing to withdraw — the jobs have to be
              dealt with first, and hiding that behind one button would leave orphaned
              work pegged to a cancelled demand. */}
          {canPlan && !cancelled && line.planned_quantity === 0 && (
            <Button size="sm" variant="ghost"
                    title="Cancel this line"
                    disabled={cancel.isPending}
                    onClick={() => cancel.mutate(line.id)}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      </td>
      )}
    </tr>
  );
}

/** @param readOnly  The order DETAIL page is customer-facing — it tells someone what
 *                    they ordered and how it is going. Authoring demand there would put
 *                    "add a line to your own order" in a customer's hands, and would
 *                    show them our planning state. Staff author lines on the internal
 *                    order editor instead. */
export function OrderLinesPanel({ orderId, readOnly = false }: {
  orderId: string; readOnly?: boolean;
}) {
  const { data, isLoading } = useOrderLines(orderId);
  const { has } = usePermissionSet();
  // Two different authorities. Recording what a customer asked for is order admin;
  // planning it commits capacity and material, which is `add_workorder`.
  const canPlan = !readOnly && has("add_workorder");
  const canAdd = !readOnly && has("add_orderline");
  const [adding, setAdding] = useState(false);

  const lines = data?.results ?? [];
  const nextLineNumber = lines.reduce((n, l) => Math.max(n, l.line_number), 0) + 1;
  const unplanned = lines
    .filter((l) => l.status !== "CANCELLED")
    .reduce((n, l) => n + l.remaining_quantity, 0);

  if (isLoading) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            Order lines
            {canAdd && !adding && (
              <Button size="sm" variant="ghost" className="h-7"
                      onClick={() => setAdding(true)}>
                <Plus className="mr-1 h-3 w-3" /> Add line
              </Button>
            )}
          </span>
          {!readOnly && unplanned > 0 && (
            <Badge variant="outline"
                   className="border-amber-500/40 text-amber-700 dark:text-amber-400">
              {unplanned} unplanned
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {lines.length === 0 && !adding ? (
          // Deliberately explicit that this is absence of demand, not absence of the
          // feature: existing orders have no lines and none were invented for them.
          <p className="text-sm text-muted-foreground">
            {readOnly
              ? "Nothing itemised on this order yet."
              : "No demand lines on this order. Lines record what the customer asked "
                + "for — a part type, a quantity and a date — and can be planned into "
                + "work orders."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-1.5">#</th>
                  <th className="px-3 py-1.5">Part type</th>
                  <th className="px-3 py-1.5 text-right">Ordered</th>
                  {!readOnly && <th className="px-3 py-1.5 text-right">Planned</th>}
                  {!readOnly && <th className="px-3 py-1.5 text-right">Remaining</th>}
                  <th className="px-3 py-1.5">Due</th>
                  {!readOnly && <th className="px-3 py-1.5"></th>}
                </tr>
              </thead>
              <tbody>
                {lines.map((l) => (
                  <LineRow key={l.id} line={l} orderId={orderId} canPlan={canPlan}
                           readOnly={readOnly} />
                ))}
                {adding && (
                  <AddLineForm orderId={orderId} nextLineNumber={nextLineNumber}
                               onDone={() => setAdding(false)} />
                )}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
