import { format } from "date-fns";
import { parseDateOnly } from "@/lib/date-only";

/** Who an FPI record's first piece is for, under its step's scope, as " for …" —
 *  " for Day Shift on 28 Oct" (Per Shift; " for the 28 Oct shift" with no shift calendar),
 *  " for CNC-1" (Per Equipment), "" per work order.
 *  Mirrors `FpiContext.label` in services/qms/fpi_scope.py. */
export function fpiForContext(r: { shift_date?: string | null; shift_info?: unknown; equipment_info?: unknown }): string {
    const machine = (r.equipment_info as { name?: unknown } | null | undefined)?.name;
    if (typeof machine === "string" && machine) return ` for ${machine}`;
    if (r.shift_date) {
        const day = format(parseDateOnly(r.shift_date), "dd MMM");
        const shift = (r.shift_info as { name?: unknown } | null | undefined)?.name;
        return typeof shift === "string" && shift ? ` for ${shift} on ${day}` : ` for the ${day} shift`;
    }
    return "";
}
