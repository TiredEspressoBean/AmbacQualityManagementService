/**
 * A location field you can scan into. Unlike LocationCombobox (a button that opens a
 * list), this is a plain input, so a handheld scanner can type a location label's code
 * straight in; matching locations are offered beneath it while typing. The value is
 * text — a name, a code or a scanned label — and the server resolves it.
 *
 * The suggestions are drawn here rather than by a native <datalist>, which offered
 * nothing inside a dialog (walk 2026-10-22, Move…).
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { locationSummaryOptions } from "@/hooks/useLocations";
import { locationFromScan } from "@/lib/scan";

const MAX_SUGGESTIONS = 8;

export function LocationInput({ value, onChange, onEnter, id, placeholder = "Scan or type a location", autoFocus }: {
    value: string;
    onChange: (v: string) => void;
    onEnter?: () => void;
    id?: string;
    placeholder?: string;
    autoFocus?: boolean;
}) {
    const { data } = useQuery(locationSummaryOptions());
    const [focused, setFocused] = useState(false);
    const [active, setActive] = useState(0);
    const needle = value.trim().toLowerCase();
    const matches = useMemo(() => {
        if (!needle) return [];
        return (data ?? [])
            .filter((l) => l.is_active)
            .filter((l) => l.name.toLowerCase().includes(needle) || l.path.toLowerCase().includes(needle))
            .filter((l) => l.name.toLowerCase() !== needle)   // already chosen
            .slice(0, MAX_SUGGESTIONS);
    }, [data, needle]);
    const open = focused && matches.length > 0;

    const pick = (name: string) => { onChange(name); setActive(0); };

    return (
        <div className="relative">
            <Input
                id={id}
                value={value}
                autoFocus={autoFocus}
                autoComplete="off"
                placeholder={placeholder}
                role="combobox"
                aria-expanded={open}
                aria-autocomplete="list"
                onFocus={() => setFocused(true)}
                // Delayed so a click on a suggestion lands before the list closes.
                onBlur={() => setTimeout(() => setFocused(false), 120)}
                onChange={(e) => { onChange(locationFromScan(e.target.value)); setActive(0); }}
                onKeyDown={(e) => {
                    if (open && e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, matches.length - 1)); }
                    else if (open && e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
                    else if (e.key === "Enter") {
                        e.preventDefault();
                        // A scanned code submits as typed; a highlighted suggestion is taken first.
                        if (open && matches[active] && matches[active].name.toLowerCase() !== needle) pick(matches[active].name);
                        else onEnter?.();
                    } else if (e.key === "Escape") setFocused(false);
                }}
            />
            {open && (
                <ul role="listbox" className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border bg-popover p-1 text-sm shadow-md">
                    {matches.map((l, i) => (
                        <li key={l.id} role="option" aria-selected={i === active}
                            className={`cursor-pointer rounded px-2 py-1.5 ${i === active ? "bg-accent" : ""}`}
                            onMouseDown={(e) => { e.preventDefault(); pick(l.name); }}
                            onMouseEnter={() => setActive(i)}>
                            <div>{l.name}</div>
                            {l.path !== l.name && <div className="text-xs text-muted-foreground">{l.path}</div>}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
