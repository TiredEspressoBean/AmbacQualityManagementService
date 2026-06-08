import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { AttrPartial } from "./useDebouncedAttrs";

/** Text-input row that preserves cursor + raw typing via local state, then
 * resyncs when the attr is externally updated (e.g. linked-spec autofill). */
export function TextAttrRow({
    attrName,
    label,
    initial,
    update,
    monospace = false,
}: {
    attrName: string;
    label: string;
    initial: string;
    update: (partial: AttrPartial) => void;
    monospace?: boolean;
}) {
    const [raw, setRaw] = useState(initial ?? "");
    useEffect(() => {
        setRaw(initial ?? "");
    }, [initial]);
    return (
        <div className="grid grid-cols-3 items-center gap-2">
            <Label className="text-xs">{label}</Label>
            <Input
                value={raw}
                onChange={(e) => {
                    setRaw(e.target.value);
                    update({ [attrName]: e.target.value });
                }}
                className={`col-span-2 h-8 text-sm${monospace ? " font-mono" : ""}`}
            />
        </div>
    );
}

/** Decimal-input row: holds a raw string locally (so "0." mid-typing
 * survives) while debouncing a parsed number into the node attrs. */
export function DecimalAttrInput({
    attrName,
    label,
    initial,
    update,
}: {
    attrName: string;
    label: string;
    initial: number | null;
    update: (partial: AttrPartial) => void;
}) {
    const [raw, setRaw] = useState(initial != null ? String(initial) : "");
    useEffect(() => {
        setRaw(initial != null ? String(initial) : "");
    }, [initial]);
    return (
        <div className="grid grid-cols-3 items-center gap-2">
            <Label className="text-xs">{label}</Label>
            <Input
                type="text"
                inputMode="decimal"
                value={raw}
                onChange={(e) => {
                    const v = e.target.value;
                    setRaw(v);
                    const parsed = v === "" ? null : Number(v);
                    update({
                        [attrName]:
                            parsed != null && Number.isFinite(parsed) ? parsed : null,
                    });
                }}
                className="col-span-2 h-8 font-mono text-sm"
            />
        </div>
    );
}
