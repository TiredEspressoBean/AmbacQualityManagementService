/**
 * Single-select searchable picker: a button that opens a Popover + Command list.
 *
 * Replaces the Popover/Command block the forms each wrote out by hand. Two things
 * those copies got wrong, handled here once:
 *
 * - the selected value's label was looked up in the CURRENT options, so with a
 *   server search typed in (or a paged list) the trigger fell back to the
 *   placeholder while a value was set. The last label seen for a value is kept,
 *   and `selectedLabel` covers a value never in any page (an edit form's initial
 *   value, say);
 * - server-searched lists were filtered a second time by cmdk on the item text.
 *   Pass `onSearch` and local filtering is off.
 *
 * `allowCreate` makes it free text with suggestions: the value is the text itself,
 * and whatever is typed can be used as is ("Use “Rack 4”").
 *
 * Works inside react-hook-form's `<FormControl>`: the props it injects (id,
 * aria-describedby, aria-invalid) land on the trigger button.
 */
import * as React from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface ComboboxOption {
    value: string;
    label: string;
    /** Secondary text under the label (a part number, a part type). */
    description?: string;
    /** Extra text the local search matches on, beside the label. */
    keywords?: string[];
    disabled?: boolean;
}

export interface ComboboxProps
    extends Omit<React.ComponentPropsWithoutRef<typeof Button>, "value" | "onChange" | "children"> {
    value: string | null | undefined;
    onChange: (value: string | null) => void;
    options: ComboboxOption[];
    /** Trigger text with nothing chosen. */
    placeholder?: string;
    searchPlaceholder?: string;
    emptyText?: string;
    /** Server-side search, called as the user types. Turns local filtering off. */
    onSearch?: (query: string) => void;
    loading?: boolean;
    /** Offer a first row that clears the value, labelled this ("No equipment type"). */
    clearLabel?: string;
    /** Label for a value that isn't among `options`. */
    selectedLabel?: string;
    /** Width of the list; defaults to the trigger's. */
    contentClassName?: string;
    /** Free text: offer what's typed as a value of its own. The value is the text. */
    allowCreate?: boolean;
}

export const Combobox = React.forwardRef<HTMLButtonElement, ComboboxProps>(function Combobox(
    {
        value, onChange, options, placeholder = "Select…", searchPlaceholder = "Search…",
        emptyText = "No matches.", onSearch, loading = false, clearLabel, selectedLabel,
        contentClassName, className, disabled, allowCreate = false, ...buttonProps
    },
    ref,
) {
    const [open, setOpen] = React.useState(false);
    const [query, setQuery] = React.useState("");

    // Remember labels as they pass through, so a selection outlives the page or
    // search result it was picked from.
    const known = React.useRef(new Map<string, string>());
    for (const o of options) known.current.set(o.value, o.label);

    const current = value ? (options.find((o) => o.value === value)?.label
        ?? known.current.get(value) ?? selectedLabel ?? (allowCreate ? value : undefined)) : undefined;
    const typed = query.trim();
    const offerTyped = allowCreate && typed !== ""
        && !options.some((o) => o.label.toLocaleLowerCase() === typed.toLocaleLowerCase());

    const search = (q: string) => {
        setQuery(q);
        onSearch?.(q);
    };
    const pick = (v: string | null) => {
        onChange(v);
        setOpen(false);
    };

    return (
        <Popover open={open} onOpenChange={(o) => { setOpen(o); if (!o && query) search(""); }}>
            <PopoverTrigger asChild>
                <Button
                    ref={ref}
                    type="button"
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    disabled={disabled}
                    className={cn("w-full justify-between font-normal", !current && "text-muted-foreground", className)}
                    {...buttonProps}
                >
                    <span className="truncate">{current ?? (value ? "Selected" : placeholder)}</span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent
                className={cn("w-[var(--radix-popover-trigger-width)] min-w-[14rem] p-0", contentClassName)}
                align="start"
            >
                <Command shouldFilter={!onSearch}>
                    <CommandInput value={query} onValueChange={search} placeholder={searchPlaceholder} />
                    <CommandList>
                        {loading ? (
                            <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                            </div>
                        ) : !offerTyped && (
                            <CommandEmpty>{emptyText}</CommandEmpty>
                        )}
                        <CommandGroup>
                            {offerTyped && (
                                // cmdk filters items by `value`; the typed text always matches itself.
                                <CommandItem value={typed} onSelect={() => pick(typed)}>
                                    <span className="mr-2 h-4 w-4" />
                                    Use “{typed}”
                                </CommandItem>
                            )}
                            {clearLabel && !query && (
                                <CommandItem value="__clear__" onSelect={() => pick(null)}>
                                    <Check className={cn("mr-2 h-4 w-4", !value ? "opacity-100" : "opacity-0")} />
                                    <span className="text-muted-foreground">{clearLabel}</span>
                                </CommandItem>
                            )}
                            {!loading && options.map((o) => (
                                <CommandItem
                                    key={o.value}
                                    // cmdk matches on `value`; keep it unique and searchable.
                                    value={`${o.label} ${o.value}`}
                                    keywords={o.keywords}
                                    disabled={o.disabled}
                                    onSelect={() => pick(o.value)}
                                >
                                    <Check className={cn("mr-2 h-4 w-4 shrink-0", o.value === value ? "opacity-100" : "opacity-0")} />
                                    <span className="flex min-w-0 flex-col">
                                        <span className="truncate">{o.label}</span>
                                        {o.description && (
                                            <span className="truncate text-xs text-muted-foreground">{o.description}</span>
                                        )}
                                    </span>
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    );
});
