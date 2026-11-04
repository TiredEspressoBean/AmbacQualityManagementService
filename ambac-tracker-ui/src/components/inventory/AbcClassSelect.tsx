/** The cycle-count class (ABC) of a material or part type: how often its stock is
 *  counted (services/mes/count_cadence). Everything starts as C; promote what matters. */
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

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
