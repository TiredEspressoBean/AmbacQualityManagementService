/**
 * Popover + Command multi-select with chips.
 *
 * Extracted from the notification rule editor; the multi-select sibling of
 * `ui/combobox`. Like it, a chip keeps its label after its item scrolls out of
 * a searched or paged list (`selectedLabels` covers ones never loaded), and a
 * server-searched list (`onSearch`) isn't filtered a second time here.
 */
import { useRef, useState } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface MultiPickerItem<T extends string | number> {
    id: T;
    label: string;
    /** Secondary text under the label. */
    description?: string;
}

export interface MultiPickerProps<T extends string | number> {
    label: string;
    items: MultiPickerItem<T>[];
    selected: T[];
    onChange: (ids: T[]) => void;
    emptyHint?: string;
    /** Hide the label above the trigger. Useful when wrapping in another control. */
    hideLabel?: boolean;
    placeholder?: string;
    disabled?: boolean;
    /** Server-side search, called as the user types. Turns local filtering off. */
    onSearch?: (query: string) => void;
    /** Labels for selected ids that may not be among `items`. */
    selectedLabels?: Partial<Record<string, string>>;
    /** A row under the items that runs something instead ("Create new error type"). */
    action?: { label: (query: string) => string; onSelect: (query: string) => void };
    searchPlaceholder?: string;
}

export function MultiPicker<T extends string | number>({
    label,
    items,
    selected,
    onChange,
    emptyHint = "No matches.",
    hideLabel = false,
    placeholder,
    disabled = false,
    onSearch,
    selectedLabels,
    action,
    searchPlaceholder,
}: MultiPickerProps<T>) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const selectedSet = new Set<string | number>(selected);
    const known = useRef(new Map<string, string>());
    for (const i of items) known.current.set(String(i.id), i.label);
    const search = (q: string) => { setQuery(q); onSearch?.(q); };

    const toggle = (id: T) => {
        if (selectedSet.has(id)) {
            onChange(selected.filter((x) => x !== id));
        } else {
            onChange([...selected, id]);
        }
    };
    const remove = (id: T) => onChange(selected.filter((x) => x !== id));

    const selectedItems = selected.map((id) => ({
        id,
        label: known.current.get(String(id)) ?? selectedLabels?.[String(id)] ?? String(id),
    }));
    const triggerText =
        selected.length === 0
            ? placeholder ?? `Add ${label.toLowerCase()}…`
            : `${selected.length} selected`;

    return (
        <div className="space-y-1.5">
            {!hideLabel && <Label className="text-xs">{label}</Label>}
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        className="w-full justify-between font-normal"
                        disabled={disabled}
                    >
                        <span className="text-muted-foreground text-xs">{triggerText}</span>
                        <ChevronsUpDown className="h-4 w-4 opacity-50" />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-72 p-0" align="start">
                    <Command shouldFilter={!onSearch}>
                        <CommandInput value={query} onValueChange={search}
                            placeholder={searchPlaceholder ?? `Search ${label.toLowerCase()}…`} />
                        <CommandList>
                            <CommandEmpty>{emptyHint}</CommandEmpty>
                            <CommandGroup>
                                {items.map((item) => (
                                    <CommandItem
                                        key={String(item.id)}
                                        value={`${item.label} ${item.id}`}
                                        onSelect={() => toggle(item.id)}
                                    >
                                        <Check
                                            className={cn(
                                                "h-4 w-4 mr-2 shrink-0",
                                                selectedSet.has(item.id) ? "opacity-100" : "opacity-0",
                                            )}
                                        />
                                        <span className="flex min-w-0 flex-col">
                                            <span className="truncate">{item.label}</span>
                                            {item.description && (
                                                <span className="truncate text-xs text-muted-foreground">{item.description}</span>
                                            )}
                                        </span>
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                            {action && (
                                <CommandGroup heading="Actions">
                                    <CommandItem value="__action__" onSelect={() => { setOpen(false); action.onSelect(query.trim()); }}>
                                        <span className="mr-2 h-4 w-4" />
                                        <span className="font-medium">{action.label(query.trim())}</span>
                                    </CommandItem>
                                </CommandGroup>
                            )}
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>
            {selectedItems.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                    {selectedItems.map((item) => (
                        <Badge key={String(item.id)} variant="secondary" className="gap-1 pr-1">
                            {item.label}
                            <button
                                type="button"
                                aria-label={`Remove ${item.label}`}
                                onClick={() => remove(item.id)}
                                className="ml-0.5 rounded hover:bg-muted-foreground/20 p-0.5"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </Badge>
                    ))}
                </div>
            )}
        </div>
    );
}