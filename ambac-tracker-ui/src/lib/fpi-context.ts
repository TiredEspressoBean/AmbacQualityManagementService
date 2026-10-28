import { format } from "date-fns";
import { parseDateOnly } from "@/lib/date-only";

/** Who an FPI record's first piece is for, under its step's scope, as " for …" —
 *  " for the 28 Oct shift" (Per Shift), " for CNC-1" (Per Equipment), "" per work order.
 *  Mirrors `FpiContext.label` in services/qms/fpi_scope.py. */
export function fpiForContext(r: { shift_date?: string | null; equipment_info?: unknown }): string {
    const machine = (r.equipment_info as { name?: unknown } | null | undefined)?.name;
    if (typeof machine === "string" && machine) return ` for ${machine}`;
    if (r.shift_date) return ` for the ${format(parseDateOnly(r.shift_date), "dd MMM")} shift`;
    return "";
}
