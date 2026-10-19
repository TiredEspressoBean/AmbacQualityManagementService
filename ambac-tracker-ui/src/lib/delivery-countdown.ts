import { differenceInCalendarDays } from "date-fns";
import { parseDateOnly } from "@/lib/date-only";

const CLOSED_STATUSES = new Set(["COMPLETED", "CANCELLED"]);

export type DeliveryCountdown =
    | { kind: "due"; days: number }      // days left, 1 or more
    | { kind: "today" }
    | { kind: "overdue"; days: number }; // days past, 1 or more

/**
 * Where an order stands against its estimated completion (a date-only field), in
 * calendar days on the viewer's clock. Null when there is no date, or when the
 * order is completed or cancelled — a closed order is not counting down or late.
 *
 * Calendar days, not `differenceInDays`: that counts whole 24-hour periods from
 * now, so an order due tomorrow read "Today" for most of the day.
 */
export function deliveryCountdown(
    estimatedCompletion: string | null | undefined,
    status: string | null | undefined,
    now: Date = new Date(),
): DeliveryCountdown | null {
    if (!estimatedCompletion || (status && CLOSED_STATUSES.has(status))) return null;
    const days = differenceInCalendarDays(parseDateOnly(estimatedCompletion), now);
    if (days > 0) return { kind: "due", days };
    if (days === 0) return { kind: "today" };
    return { kind: "overdue", days: -days };
}
