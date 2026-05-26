/**
 * Popover + Command multi-select with chips.
 *
 * Extracted from the notification rule editor; the same pattern appears
 * inline in `AddPartsForm`, `part-disposition-form`, `part-quality-form`,
 * and `flow/step-documents-editor`. Those callsites should migrate to
 * this primitive over time.
 */
import { useState } from "react";
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
}: MultiPickerProps<T>) {
    const [open, setOpen] = useState(false);
    const selectedSet = new Set<string | number>(selected);

    const toggle = (id: T) => {
        if (selectedSet.has(id)) {
            onChange(selected.filter((x) => x !== id));
        } else {
            onChange([...selected, id]);
        }
    };
    const remove = (id: T) => onChange(selected.filter((x) => x !== id));

    const selectedItems = items.filter((i) => selectedSet.has(i.id));
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
                    <Command>
                        <CommandInput placeholder={`Search ${label.toLowerCase()}…`} />
                        <CommandList>
                            <CommandEmpty>{emptyHint}</CommandEmpty>
                            <CommandGroup>
                                {items.map((item) => (
                                    <CommandItem
                                        key={String(item.id)}
                                        onSelect={() => toggle(item.id)}
                                    >
                                        <Check
                                            className={cn(
                                                "h-4 w-4 mr-2",
                                                selectedSet.has(item.id) ? "opacity-100" : "opacity-0",
                                            )}
                                        />
                                        {item.label}
                                    </CommandItem>
                                ))}
                            </CommandGroup>
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