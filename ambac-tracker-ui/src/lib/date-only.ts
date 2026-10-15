import { parseISO } from "date-fns";

/**
 * Parse a **date-only** value — `"2026-10-06"`, what DRF's `DateField` serialises —
 * as local midnight.
 *
 * `new Date("2026-10-06")` reads a bare date as UTC midnight, which in any zone
 * behind UTC is the previous evening: in America/New_York it becomes Oct 5 20:00,
 * and every format call then renders the 5th. The value is stored correctly; only
 * the reading is wrong, so no backend test can see it and it shows up for exactly
 * the users who are behind UTC. `parseISO` reads the same string as local midnight.
 *
 * **Only for date-only fields.** A full datetime (`DateTimeField`, the `_at`
 * convention) already round-trips correctly through `new Date`, and routing one
 * through here would be a regression, not a fix. The serialiser's field type is the
 * authority — `format: date` in `schema.yaml` means date-only and belongs here,
 * `format: date-time` does not.
 */
export function parseDateOnly(value: string): Date {
    return parseISO(value);
}
