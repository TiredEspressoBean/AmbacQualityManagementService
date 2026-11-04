/** The cycle-count class (ABC) of a material or part type: how often its stock is
 *  counted (services/mes/count_cadence). Everything starts as C; promote what matters. */
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { itemCountStatusOptions } from "@/hooks/useCycleCounts";
import { usePermissionSet } from "@/hooks/useMyPermissions";

export type AbcClass = "A" | "B" | "C";

export const ABC_HINT =
    "How often its stock is cycle-counted: A most often, C least. The intervals are set " +
    "under Organization settings. Everything starts as C.";

const LABEL: Record<AbcClass, string> = {
    A: "A — counted most often",
    B: "B — counted regularly",
    C: "C — counted least often",
};

export function AbcClassSelect({ value, onChange, disabled, id }: {
    value: AbcClass | null | undefined;
    onChange: (v: AbcClass) => void;
    disabled?: boolean;
    id?: string;
}) {
    return (
        <Select value={value ?? "C"} onValueChange={(v) => v && onChange(v as AbcClass)}
            {...(disabled ? { disabled: true } : {})}>
            <SelectTrigger id={id} className="w-56"><SelectValue /></SelectTrigger>
            <SelectContent>
                {(["A", "B", "C"] as const).map((c) => (
                    <SelectItem key={c} value={c}>{LABEL[c]}</SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

/** "YYYY-MM-DD" as a local date, so it doesn't shift a day west of UTC. */
const localDate = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
};

/** When this item was last counted and is next due, by its saved class — the same
 *  terms as the Due list on Cycle Counts. Hidden without view_cyclecount. */
export function CountStatusLine({ item }: { item: { material: string } | { part_type: string } }) {
    const canView = usePermissionSet().has("view_cyclecount");
    const { data: st } = useQuery({ ...itemCountStatusOptions(item), enabled: canView });
    if (!canView || !st) return null;
    if (!st.on_hand) {
        return <p className="text-sm text-muted-foreground">No stock in a location, so nothing to count.</p>;
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = st.next_due ? localDate(st.next_due) : null;
    const overdue = due != null && due < today;
    const dueNow = due != null && !overdue && due.getTime() === today.getTime();
    const firstDue = st.locations[0];
    return (
        <div className="text-sm" title={st.locations.map((l) =>
            `${l.location}: ${l.last_counted ? `counted ${new Date(l.last_counted).toLocaleDateString()}` : "never counted"}, due ${localDate(l.due_on).toLocaleDateString()}`,
        ).join("\n")}>
            <span className="text-muted-foreground">Last counted </span>
            {st.last_counted ? new Date(st.last_counted).toLocaleDateString() : "never"}
            <span className="text-muted-foreground"> · next due </span>
            <span className={overdue || dueNow ? "font-medium text-amber-700 dark:text-amber-400" : undefined}>
                {due == null ? "—" : overdue ? `${due.toLocaleDateString()} (overdue)` : dueNow ? "now" : due.toLocaleDateString()}
            </span>
            {st.locations.length > 1 && firstDue && (
                <span className="text-muted-foreground"> at {firstDue.location}{st.never_counted ? ", never counted there" : ""}</span>
            )}
            <span className="text-muted-foreground"> · every {st.interval_days} days as class {st.abc_class}</span>
            {(overdue || dueNow) && (
                <> · <Link to="/production/cycle-counts" className="underline">Cycle counts</Link></>
            )}
        </div>
    );
}
