/**
 * A location field you can scan into. Unlike LocationCombobox (a button that opens a
 * list), this is a plain input, so a handheld scanner can type a location label's code
 * straight in; the locations are offered as suggestions while typing. The value is
 * text — a name, a code or a scanned label — and the server resolves it.
 */
import { useId } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { locationSummaryOptions } from "@/hooks/useLocations";
import { locationFromScan } from "@/lib/scan";

export function LocationInput({ value, onChange, onEnter, id, placeholder = "Scan or type a location", autoFocus }: {
    value: string;
    onChange: (v: string) => void;
    onEnter?: () => void;
    id?: string;
    placeholder?: string;
    autoFocus?: boolean;
}) {
    const listId = useId();
    const { data } = useQuery(locationSummaryOptions());
    return (
        <>
            <Input
                id={id}
                list={listId}
                value={value}
                autoFocus={autoFocus}
                placeholder={placeholder}
                onChange={(e) => onChange(locationFromScan(e.target.value))}
                onKeyDown={(e) => { if (e.key === "Enter" && onEnter) { e.preventDefault(); onEnter(); } }}
            />
            <datalist id={listId}>
                {(data ?? []).filter((l) => l.is_active).map((l) =>
                    <option key={l.id} value={l.name}>{l.path !== l.name ? l.path : undefined}</option>)}
            </datalist>
        </>
    );
}
