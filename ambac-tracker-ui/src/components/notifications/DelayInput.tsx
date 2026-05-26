/**
 * Number + unit picker for escalation/coverage step delays. Storage is
 * always seconds; the unit is a UI affordance only.
 */
import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export type DelayUnit = "min" | "hr" | "day";

interface Props {
    seconds: number;
    onChange: (seconds: number) => void;
}

export function DelayInput({ seconds, onChange }: Props) {
    const initial = pickUnit(seconds);
    const [value, setValue] = useState<number>(initial.value);
    const [unit, setUnit] = useState<DelayUnit>(initial.unit);

    // Keep local UI state in sync when `seconds` is updated externally
    // (e.g., editor loads a fresh rule into the same component instance).
    useEffect(() => {
        const next = pickUnit(seconds);
        setValue(next.value);
        setUnit(next.unit);
    }, [seconds]);

    const apply = (v: number, u: DelayUnit) => {
        const mult = u === "min" ? 60 : u === "hr" ? 3600 : 86400;
        onChange(Math.max(0, v * mult));
    };

    return (
        <div className="inline-flex items-center gap-1">
            <Input
                type="number"
                min={0}
                value={value}
                onChange={(e) => {
                    const v = e.target.value === "" ? 0 : Number(e.target.value);
                    setValue(v);
                    apply(v, unit);
                }}
                className="h-8 w-20 text-sm"
            />
            <Select
                value={unit}
                onValueChange={(u) => {
                    const next = u as DelayUnit;
                    setUnit(next);
                    apply(value, next);
                }}
            >
                <SelectTrigger className="h-8 w-24 text-sm">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="min">minutes</SelectItem>
                    <SelectItem value="hr">hours</SelectItem>
                    <SelectItem value="day">days</SelectItem>
                </SelectContent>
            </Select>
        </div>
    );
}

function pickUnit(seconds: number): { value: number; unit: DelayUnit } {
    if (seconds === 0) return { value: 0, unit: "hr" };
    if (seconds % 86400 === 0) return { value: seconds / 86400, unit: "day" };
    if (seconds % 3600 === 0) return { value: seconds / 3600, unit: "hr" };
    return { value: Math.max(1, Math.round(seconds / 60)), unit: "min" };
}
